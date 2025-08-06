# --- Importações de Ferramentas ---
import os
from datetime import datetime, date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (Flask, render_template, request, redirect, url_for,
                   session, send_from_directory, flash)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

# --- Configuração Geral do Aplicativo ---
app = Flask(__name__)

# TODO: INSIRA SUA SENHA DO AWS RDS AQUI
DB_USER = "admin"
DB_PASSWORD = "1IWldUPFxXHkAHytNnye"  # <--- COLOQUE SUA SENHA AQUI
DB_HOST = "gsme-database.catcqusiwhir.us-east-1.rds.amazonaws.com"
DB_PORT = "3306"
DB_NAME = "gsme"

# --- Configuração do SQLAlchemy ---
app.config['SECRET_KEY'] = 'gK4bV7cZ2xN1mS6jH8fD3aT'
# A string de conexão é montada com os dados acima
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

ADMIN_ACCESS_KEY = "SMEitace06"

# Garante que a pasta 'uploads' exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializa a extensão SQLAlchemy
db = SQLAlchemy(app)


# --- Modelos de Banco de Dados (Tabelas) ---
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='subordinado')

    def __repr__(self):
        return f'<Usuario {self.username}>'

class Solicitacao(db.Model):
    __tablename__ = 'solicitacao'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(300), nullable=False)
    prazo = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pendente')
    assigned_to_username = db.Column(db.String(80), nullable=False)
    arquivo_path = db.Column(db.String(300), nullable=True)
    data_entrega = db.Column(db.Date, nullable=True)

    # Adiciona uma propriedade para facilitar o acesso ao objeto usuário
    assignee = db.relationship('Usuario', foreign_keys=[assigned_to_username], primaryjoin="Solicitacao.assigned_to_username == Usuario.username", backref='solicitacao')

    def __repr__(self):
        return f'<Solicitacao {self.id}>'

# --- Decoradores (Filtros de Acesso para as Páginas) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Acesso restrito a administradores.", "warning")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def subordinate_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'subordinado':
            flash("Acesso restrito a subordinados.", "warning")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- Funções Auxiliares ---
def get_subordinates():
    """Busca e retorna uma lista com o nome de todos os usuários subordinados."""
    subordinates = db.session.execute(db.select(Usuario).filter_by(role='subordinado')).scalars().all()
    return [s.username for s in subordinates]

def processar_solicitacao(solicitacao_obj):
    """Adiciona informações úteis (cor de status e link de download) a uma solicitacao de serviço."""
    solicitacao_dict = {
        'id': solicitacao_obj.id,
        'descricao': solicitacao_obj.descricao,
        'prazo': solicitacao_obj.prazo.strftime('%Y-%m-%d'),
        'status': solicitacao_obj.status,
        'assigned_to_username': solicitacao_obj.assigned_to_username,
        'arquivo_path': solicitacao_obj.arquivo_path,
        'data_entrega': solicitacao_obj.data_entrega.strftime('%Y-%m-%d') if solicitacao_obj.data_entrega else None,
        'status_class': '',
        'download_link': None
    }
    
    solicitacao_prazo = solicitacao_obj.prazo
    
    if solicitacao_obj.status == 'Entregue':
        data_entrega = solicitacao_obj.data_entrega
        if data_entrega and solicitacao_prazo:
            solicitacao_dict['status_class'] = 'entregue-a-tempo' if data_entrega <= solicitacao_prazo else 'atrasado'
    elif solicitacao_prazo < date.today():
        solicitacao_dict['status_class'] = 'atrasado'
    
    if solicitacao_obj.arquivo_path:
        solicitacao_dict['download_link'] = url_for('uploaded_file', filename=os.path.basename(solicitacao_obj.arquivo_path))
        
    return solicitacao_dict

# --- Rotas da Aplicação (Páginas do Site) ---
@app.route('/')
@login_required
def home():
    if session['role'] == 'admin':
        # Se for admin, redireciona para o painel de admin
        return redirect(url_for('admin_dashboard'))
    else:
        # Senão, redireciona para o painel de subordinado
        return redirect(url_for('subordinate_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.session.execute(db.select(Usuario).filter_by(username=username)).scalar_one_or_none()
        
        if user and check_password_hash(user.password_hash, password):
            session['logged_in'] = True
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Você foi desconectado com sucesso.", "info")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.form.get('access_key') != ADMIN_ACCESS_KEY:
            flash("Chave de acesso de administrador inválida.", 'danger')
            return render_template('register.html')
        
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        new_admin = Usuario(username=username, password_hash=hashed_password, role='admin')
        
        try:
            db.session.add(new_admin)
            db.session.commit()
            flash(f"Administrador '{username}' registrado com sucesso! Faça o login.", "success")
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash(f"Usuário '{username}' já existe.", 'danger')
            
    return render_template('register.html')

# --- Rotas Exclusivas do Administrador ---
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    selected_sub = request.args.get('subordinate')
    
    stmt = db.select(Solicitacao).order_by(Solicitacao.prazo.asc())

    if selected_sub:
        stmt = stmt.filter_by(assigned_to_username=selected_sub)
    
    solicitacoes = db.session.execute(stmt).scalars().all() 
    solicitacoes_processadas = [processar_solicitacao(o) for o in solicitacoes]
    
    return render_template('admin.html', 
                           solicitacoes=solicitacoes_processadas, 
                           subordinates=get_subordinates(), 
                           selected_sub=selected_sub)

@app.route('/admin/create_subordinate_page')
@admin_required
def create_subordinate_page():
    return render_template('create_subordinate.html')

@app.route('/admin/create_subordinate', methods=['POST'])
@admin_required
def admin_create_subordinate():
    username = request.form['username']
    password = request.form['password']
    
    hashed_password = generate_password_hash(password)
    new_subordinate = Usuario(username=username, password_hash=hashed_password, role='subordinado')

    try:
        db.session.add(new_subordinate)
        db.session.commit()
        flash(f"Subordinado '{username}' criado com sucesso.", "success")
        return redirect(url_for('admin_dashboard'))
    except IntegrityError:
        db.session.rollback()
        flash(f"Usuário '{username}' já existe.", 'danger')
        return redirect(url_for('create_subordinate_page'))

@app.route('/adicionar_solicitacao', methods=['POST'])
@admin_required
def adicionar_solicitacao():
    descricao = request.form['descricao']
    prazo_str = request.form['prazo']
    assigned_to = request.form['assigned_to_username']

    try:
        prazo = datetime.strptime(prazo_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Formato de data inválido. Use AAAA-MM-DD.", "danger")
        return redirect(url_for('admin_dashboard'))

    nova_solicitacao = Solicitacao(
        descricao=descricao,
        prazo=prazo,
        assigned_to_username=assigned_to
    )
    
    db.session.add(nova_solicitacao)
    db.session.commit()
    flash("Nova solicitacao de serviço adicionada com sucesso.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/deletar_solicitacao/<int:id>')
@admin_required
def deletar_solicitacao(id):
    solicitacao_para_deletar = db.get_or_404(Solicitacao, id)
    
    if solicitacao_para_deletar.arquivo_path and os.path.exists(solicitacao_para_deletar.arquivo_path):
        try:
            os.remove(solicitacao_para_deletar.arquivo_path)
        except OSError as e:
            flash(f"Erro ao deletar arquivo associado: {e}", "danger")
            
    db.session.delete(solicitacao_para_deletar)
    db.session.commit()
    flash("solicitacao de serviço deletada com sucesso.", "success")
    return redirect(url_for('admin_dashboard'))

# --- Rotas Exclusivas do Subordinado ---
@app.route('/subordinate/dashboard')
@subordinate_required
def subordinate_dashboard():
    stmt = db.select(Solicitacao).filter_by(
        assigned_to_username=session['username']
    ).order_by(Solicitacao.prazo.asc())
    
    solicitacao = db.session.execute(stmt).scalars().all()
    solicitacao_processadas = [processar_solicitacao(o) for o in solicitacao]
    return render_template('subordinate.html', solicitacao=solicitacao_processadas)

@app.route('/upload_arquivo/<int:id>', methods=['POST'])
@subordinate_required
def upload_arquivo(id):
    arquivo = request.files.get('arquivo')
    if not arquivo or arquivo.filename == '':
        flash("Nenhum arquivo selecionado.", "warning")
        return redirect(url_for('subordinate_dashboard'))
    
    solicitacao = db.session.execute(
        db.select(Solicitacao).filter_by(id=id, assigned_to_username=session['username'])
    ).scalar_one_or_none()

    if not solicitacao:
        flash("solicitacao de serviço não encontrada ou não pertence a você.", "danger")
        return redirect(url_for('subordinate_dashboard'))
    
    filename = f"{id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{arquivo.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    arquivo.save(filepath)

    solicitacao.arquivo_path = filepath
    solicitacao.status = 'Entregue'
    solicitacao.data_entrega = date.today()
    
    db.session.commit()
    flash("Arquivo enviado e solicitacao marcada como 'Entregue'.", "success")
    return redirect(url_for('subordinate_dashboard'))

# --- Rota para Download de Arquivos ---
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# --- Ponto de Partida da Aplicação ---
if __name__ == '__main__':
    with app.app_context():
        # Descomente a linha abaixo na primeira vez que rodar para criar as tabelas
        # db.create_all()
        pass
    # Em um ambiente de produção, use um servidor WSGI como Gunicorn ou Waitress
    # e remova debug=True
    app.run(host='0.0.0.0', debug=True)
