-- Cria a tabela de usuários se ela não existir.
-- Utiliza INT para o ID com AUTO_INCREMENT para geração automática.
-- VARCHAR é usado para campos de texto com tamanho definido, o que é mais eficiente.
CREATE TABLE IF NOT EXISTS usuarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL
);

-- Cria a tabela de ordens de serviço se ela não existir.
-- O tipo DATE é usado para os campos de prazo e data de entrega para melhor manipulação de datas.
-- Adiciona uma chave estrangeira (FOREIGN KEY) para garantir a integridade referencial com a tabela de usuários.
CREATE TABLE IF NOT EXISTS solicitacao (
    id INT PRIMARY KEY AUTO_INCREMENT,
    descricao TEXT,
    prazo DATE,
    arquivo_path VARCHAR(255),
    arquivo_url VARCHAR(512),
    status VARCHAR(50),
    data_entrega DATE,
    assigned_to_username VARCHAR(255),
    FOREIGN KEY (assigned_to_username) REFERENCES usuarios(username)
);