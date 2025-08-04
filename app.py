# app.py (Versão Refatorada com Comentários em cada linha)

# --- Importações de Ferramentas ---
# Importa as classes principais do Flask para criar o site.
from flask import (Flask, render_template, request, redirect, url_for,
                   session, send_from_directory, flash)
# Importa a biblioteca para interagir com o banco de dados SQLite.
import sqlite3
# Importa a biblioteca para interagir com o sistema operacional (pastas, arquivos).
import os
# Importa ferramentas para trabalhar com datas e horas.
from datetime import datetime, date
# Importa funções para criar e verificar senhas de forma segura.
from werkzeug.security import generate_password_hash, check_password_hash
# Importa uma ferramenta auxiliar para construir nossos decoradores.
from functools import wraps

# --- Configuração Geral do Aplicativo ---
# Cria a aplicação Flask.
app = Flask(__name__)
# Define uma chave secreta para proteger os dados da sessão (login).
app.secret_key = 'sua_chave_secreta'
# Define o nome da pasta onde os arquivos de upload serão salvos.
UPLOAD_FOLDER = 'uploads'
# Configura o Flask para usar essa pasta de upload.
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Garante que a pasta 'uploads' exista; se não, ela é criada.
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Define o nome do arquivo do nosso banco de dados.
DATABASE = 'database.db'
# Define a chave de acesso especial para registrar novos administradores.
ADMIN_ACCESS_KEY = "SMEitace06"

# --- Funções de Gerenciamento do Banco de Dados ---
def get_db_connection():
    """Esta função cria e retorna uma conexão com o banco de dados."""
    # Conecta ao arquivo do banco de dados SQLite.
    conn = sqlite3.connect(DATABASE)
    # Configura a conexão para retornar os resultados como dicionários (acesso por nome da coluna).
    conn.row_factory = sqlite3.Row
    # Retorna a conexão pronta para uso.
    return conn

def init_db():
    """Esta função cria as tabelas no banco de dados, se elas ainda não existirem."""
    # Usa 'with' para garantir que a conexão seja fechada automaticamente.
    with get_db_connection() as conn:
        # Executa o comando SQL para criar a tabela de usuários.
        conn.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT)')
        # Executa o comando SQL para criar a tabela de ordens de serviço.
        conn.execute('CREATE TABLE IF NOT EXISTS ordens_servico (id INTEGER PRIMARY KEY, descricao TEXT, prazo TEXT, arquivo_path TEXT, status TEXT, data_entrega TEXT, assigned_to_username TEXT)')
        # Salva as alterações feitas no banco de dados.
        conn.commit()

# Executa a função de inicialização do banco de dados quando o aplicativo começa.
with app.app_context():
    init_db()

# --- Decoradores (Filtros de Acesso para as Páginas) ---
def login_required(f):
    """Este decorador verifica se um usuário está logado."""
    # Preserva o nome e outras informações da função original.
    @wraps(f)
    # A nova função que substitui a original.
    def decorated_function(*args, **kwargs):
        # Se 'logged_in' não estiver na sessão, o usuário não está logado.
        if 'logged_in' not in session:
            # Redireciona o usuário para a página de login.
            return redirect(url_for('login'))
        # Se estiver logado, permite que a função original seja executada.
        return f(*args, **kwargs)
    # Retorna a função modificada.
    return decorated_function

def admin_required(f):
    """Este decorador verifica se o usuário logado é um administrador."""
    @wraps(f)
    # Aplica primeiro o filtro de login.
    @login_required
    def decorated_function(*args, **kwargs):
        # Se o papel do usuário na sessão não for 'admin'.
        if session.get('role') != 'admin':
            # Redireciona para a página inicial.
            return redirect(url_for('home'))
        # Se for admin, executa a função da página.
        return f(*args, **kwargs)
    return decorated_function

def subordinate_required(f):
    """Este decorador verifica se o usuário logado é um subordinado."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Se o papel do usuário na sessão não for 'subordinado'.
        if session.get('role') != 'subordinado':
            # Redireciona para a página inicial.
            return redirect(url_for('home'))
        # Se for subordinado, executa a função da página.
        return f(*args, **kwargs)
    return decorated_function

# --- Funções Auxiliares ---
def get_subordinates():
    """Busca e retorna uma lista com o nome de todos os usuários subordinados."""
    with get_db_connection() as conn:
        # Executa uma busca por todos os usuários com o papel 'subordinado'.
        subordinates = conn.execute("SELECT username FROM usuarios WHERE role = 'subordinado'").fetchall()
    # Retorna apenas os nomes de usuário em uma lista simples.
    return [s['username'] for s in subordinates]

def processar_ordem(ordem_row):
    """Adiciona informações úteis (cor de status e link de download) a uma ordem de serviço."""
    # Converte a linha do banco de dados em um dicionário.
    ordem = dict(ordem_row)
    # Converte o prazo (texto) para um objeto de data.
    ordem_prazo = datetime.strptime(ordem['prazo'], '%Y-%m-%d').date()
    # Inicia a classe de status como vazia.
    ordem['status_class'] = ''
    # Se a ordem foi entregue...
    if ordem['status'] == 'Entregue':
        # Converte a data de entrega (texto) para um objeto de data.
        data_entrega = datetime.strptime(ordem['data_entrega'], '%Y-%m-%d').date()
        # Define a classe como 'entregue-a-tempo' ou 'atrasado' comparando as datas.
        ordem['status_class'] = 'entregue-a-tempo' if data_entrega <= ordem_prazo else 'atrasado'
    # Se não foi entregue e o prazo já passou...
    elif ordem_prazo < date.today():
        # Define a classe como 'atrasado'.
        ordem['status_class'] = 'atrasado'
    
    # Se existe um caminho de arquivo salvo para esta ordem...
    if ordem['arquivo_path']:
        # Cria um link de download para o arquivo.
        ordem['download_link'] = url_for('uploaded_file', filename=os.path.basename(ordem['arquivo_path']))
    # Se não existe um arquivo...
    else:
        # O link de download é nulo.
        ordem['download_link'] = None
    # Retorna a ordem com as novas informações.
    return ordem

# --- Rotas da Aplicação (Páginas do Site) ---
# Define a URL da página inicial.
@app.route('/')
# Exige que o usuário esteja logado para acessar.
@login_required
def home():
    """Página inicial que redireciona o usuário para seu painel correto."""
    # Se o usuário for admin, vai para o painel de admin. Senão, para o de subordinado.
    return redirect(url_for('admin_dashboard')) if session['role'] == 'admin' else redirect(url_for('subordinate_dashboard'))

# Define a URL para a página de login, aceitando métodos GET (carregar a pág) e POST (enviar formulário).
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página para o usuário fazer login."""
    # Se o formulário foi enviado (método POST).
    if request.method == 'POST':
        # Pega o usuário no banco de dados pelo nome de usuário informado.
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM usuarios WHERE username = ?', (request.form['username'],)).fetchone()
        # Se o usuário existe e a senha está correta...
        if user and check_password_hash(user['password_hash'], request.form['password']):
            # Atualiza a sessão com os dados do usuário.
            session.update(logged_in=True, username=user['username'], role=user['role'])
            # Redireciona para a página inicial.
            return redirect(url_for('home'))
        # Se o usuário ou senha estiverem errados, mostra uma mensagem de erro.
        flash('Usuário ou senha inválidos.', 'danger')
    # Se for método GET, apenas mostra a página de login.
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Rota para fazer o logout do usuário."""
    # Limpa todos os dados da sessão.
    session.clear()
    # Redireciona para a página de login.
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Página para registrar um novo administrador."""
    if request.method == 'POST':
        # Se a chave de acesso informada for diferente da chave correta...
        if request.form.get('access_key') != ADMIN_ACCESS_KEY:
            # Mostra uma mensagem de erro.
            flash("Chave de acesso de administrador inválida.", 'danger')
            # Mostra a página de registro novamente.
            return render_template('register.html')
        # Tenta inserir o novo usuário no banco de dados.
        try:
            with get_db_connection() as conn:
                # Insere os dados, com a senha criptografada e o papel 'admin'.
                conn.execute('INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)',
                             (request.form['username'], generate_password_hash(request.form['password']), 'admin'))
                # Salva a alteração.
                conn.commit()
            # Redireciona para a página de login após o sucesso.
            return redirect(url_for('login'))
        # Se o usuário já existir, o banco de dados retornará um erro de integridade.
        except sqlite3.IntegrityError:
            # Mostra uma mensagem de erro informando que o usuário já existe.
            flash(f"Usuário '{request.form['username']}' já existe.", 'danger')
    # Mostra a página de registro.
    return render_template('register.html')

# --- Rotas Exclusivas do Administrador ---
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Painel principal do administrador."""
    # Pega o subordinado selecionado no filtro da URL, se houver.
    selected_sub = request.args.get('subordinate')

    with get_db_connection() as conn:
        # Prepara a base da consulta SQL.
        query = 'SELECT * FROM ordens_servico'
        params = []

        # Se um subordinado específico foi selecionado no filtro...
        if selected_sub:
            # Adiciona a condição WHERE na consulta.
            query += ' WHERE assigned_to_username = ?'
            params.append(selected_sub)

        # Adiciona a ordenação por prazo.
        query += ' ORDER BY prazo ASC'

        # Executa a consulta com os parâmetros (se houver).
        ordens = conn.execute(query, tuple(params)).fetchall()

    # Processa cada ordem para adicionar status_class e download_link.
    ordens_processadas = [processar_ordem(o) for o in ordens]
    
    # Mostra a página, passando a lista de ordens, de subordinados e o subordinado atualmente selecionado no filtro.
    return render_template('admin.html', ordens=ordens_processadas, subordinates=get_subordinates(), selected_sub=selected_sub)


@app.route('/admin/create_subordinate_page')
@admin_required
def create_subordinate_page():
    """Mostra a página com o formulário para criar um novo subordinado."""
    return render_template('create_subordinate.html')

@app.route('/admin/create_subordinate', methods=['POST'])
@admin_required
def admin_create_subordinate():
    """Processa o formulário e cria um novo usuário subordinado no sistema."""
    try:
        # Tenta inserir o novo subordinado no banco.
        with get_db_connection() as conn:
            conn.execute('INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)',
                         (request.form['username'], generate_password_hash(request.form['password']), 'subordinado'))
            conn.commit()
        # Redireciona para o painel do admin.
        return redirect(url_for('admin_dashboard'))
    except sqlite3.IntegrityError:
        # Se o usuário já existir, mostra um erro.
        flash(f"Usuário '{request.form['username']}' já existe.", 'danger')
        # Redireciona de volta para a página de criação.
        return redirect(url_for('create_subordinate_page'))

@app.route('/adicionar_ordem', methods=['POST'])
@admin_required
def adicionar_ordem():
    """Adiciona uma nova ordem de serviço no banco de dados."""
    with get_db_connection() as conn:
        # Insere os dados do formulário na tabela de ordens de serviço.
        conn.execute('INSERT INTO ordens_servico (descricao, prazo, status, assigned_to_username) VALUES (?, ?, ?, ?)',
                     (request.form['descricao'], request.form['prazo'], 'Pendente', request.form['assigned_to_username']))
        conn.commit()
    # Redireciona de volta ao painel do admin.
    return redirect(url_for('admin_dashboard'))

@app.route('/deletar_ordem/<int:id>')
@admin_required
def deletar_ordem(id):
    """Deleta uma ordem de serviço e, se houver, seu arquivo associado."""
    with get_db_connection() as conn:
        # Busca a ordem para encontrar o caminho do arquivo.
        ordem = conn.execute('SELECT arquivo_path FROM ordens_servico WHERE id = ?', (id,)).fetchone()
        # Se a ordem existe e tem um arquivo...
        if ordem and ordem['arquivo_path']:
            # Se o arquivo realmente existe na pasta...
            if os.path.exists(ordem['arquivo_path']):
                # Remove o arquivo do servidor.
                os.remove(ordem['arquivo_path'])
        # Deleta a ordem da tabela no banco de dados.
        conn.execute('DELETE FROM ordens_servico WHERE id = ?', (id,))
        # Salva a remoção.
        conn.commit()
    # Redireciona de volta para o painel do admin.
    return redirect(url_for('admin_dashboard'))

# --- Rotas Exclusivas do Subordinado ---
@app.route('/subordinate/dashboard')
@subordinate_required
def subordinate_dashboard():
    """Painel principal do subordinado."""
    # Busca no banco de dados apenas as ordens atribuídas a este usuário.
    with get_db_connection() as conn:
        ordens = conn.execute('SELECT * FROM ordens_servico WHERE assigned_to_username = ? ORDER BY prazo ASC', (session['username'],)).fetchall()
    # Processa cada ordem para adicionar informações extras.
    ordens_processadas = [processar_ordem(o) for o in ordens]
    # Mostra a página do painel do subordinado com suas ordens.
    return render_template('subordinate.html', ordens=ordens_processadas)

@app.route('/upload_arquivo/<int:id>', methods=['POST'])
@subordinate_required
def upload_arquivo(id):
    """Processa o envio de um arquivo para completar uma ordem de serviço."""
    # Pega o arquivo do formulário.
    arquivo = request.files.get('arquivo')
    # Se nenhum arquivo foi enviado...
    if not arquivo:
        # Volta para o painel do subordinado.
        return redirect(url_for('subordinate_dashboard'))
    
    with get_db_connection() as conn:
        # Verifica se a ordem pertence mesmo a este usuário.
        ordem = conn.execute('SELECT * FROM ordens_servico WHERE id = ? AND assigned_to_username = ?', (id, session['username'])).fetchone()
        # Se a ordem não for encontrada (não pertence a ele)...
        if not ordem:
            # Volta para o painel.
            return redirect(url_for('subordinate_dashboard'))
        
        # Cria um nome de arquivo único para evitar sobreposições.
        filename = f"{id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{arquivo.filename}"
        # Cria o caminho completo onde o arquivo será salvo.
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Salva o arquivo no caminho definido.
        arquivo.save(filepath)

        # Atualiza a ordem no banco de dados com o caminho do arquivo e o status 'Entregue'.
        conn.execute('UPDATE ordens_servico SET arquivo_path = ?, status = ?, data_entrega = ? WHERE id = ?',
                     (filepath, 'Entregue', date.today().strftime('%Y-%m-%d'), id))
        # Salva a alteração.
        conn.commit()
    # Redireciona de volta ao painel do subordinado.
    return redirect(url_for('subordinate_dashboard'))

# --- Rota para Download de Arquivos ---
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
   """Permite que usuários logados baixem os arquivos da pasta 'uploads'."""
   # Envia o arquivo do diretório especificado, forçando o download.
   return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# --- Ponto de Partida da Aplicação ---
# Verifica se este script está sendo executado diretamente.
if __name__ == '__main__':
    # Inicia o servidor web do Flask em modo de depuração (mostra erros e atualiza automaticamente).
    app.run(debug=True)