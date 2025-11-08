import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
# NOVAS BIBLIOTECAS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- Configuração ---
app = Flask(__name__)
CORS(app) 
# Chave secreta (necessária para o Flask-Login)
app.config['SECRET_KEY'] = 'La9QdfPQj0aGUq3RDKRyxdP5suXn3TPEWDMj0olWaN2'

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DATABASE_URL = os.environ.get('DATABASE_URL') # O Render vai nos dar esta URL
if not DATABASE_URL:
    # Se rodando local, use a URL que tínhamos (mude para a sua)
    DATABASE_URL = "postgresql://rango_amigo_db_user:Fyrzpverx24tmioZRgHKOX8NDwBBEIG4@dpg-d47m05umcj7s73dfsde0-a.oregon-postgres.render.com/rango_amigo_db"
    print("Atenção: Rodando com banco de dados local (fallback).")

# Corrigindo a URL para o SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# --- NOVAS INICIALIZAÇÕES ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Nome da ROTA de login
login_manager.login_message_category = 'info' # Categoria do Bootstrap para 'flash'

# --- Novos Modelos de Banco de Dados ---

@login_manager.user_loader
def load_user(user_id):
    """Função que o Flask-Login usa para recarregar o usuário da sessão"""
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    """Novo modelo para Usuários"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Senha terá 60 caracteres por causa do hash do Bcrypt
    password_hash = db.Column(db.String(60), nullable=False)
    
    # Relação: "Minhas doações"
    # 'Doacao' é o nome da Classe
    # 'author' é como a Doacao vai se referir ao User (ex: doacao.author)
    # 'lazy=True' significa que o SQLAlchemy só carrega esses dados quando pedirmos
    doacoes = db.relationship('Doacao', backref='author', lazy=True)

class Doacao(db.Model):
    """Modelo de Doação MODIFICADO"""
    id = db.Column(db.Integer, primary_key=True)
    nome_local = db.Column(db.String(100), nullable=False)
    itens = db.Column(db.Text, nullable=False)
    horario_retirada = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    # --- MUDANÇA IMPORTANTE ---
    # Chave estrangeira que liga esta Doação a um Usuário
    # 'user.id' é o nome da tabela 'user' e coluna 'id'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nome_local": self.nome_local,
            "itens": self.itens,
            "horario_retirada": self.horario_retirada,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "author_email": self.author.email # Bônus: agora podemos mostrar quem postou
        }

# --- ROTAS DAS PÁGINAS HTML ---

@app.route('/')
def home():
    """Rota do Mapa (não muda)"""
    return render_template('index.html')

@app.route('/postar')
@login_required # <-- MÁGICA: Esta página agora exige login
def postar_page():
    """Rota da página de cadastro"""
    return render_template('postar.html')

# --- ROTAS DE AUTENTICAÇÃO (NOVAS) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Se o usuário já estiver logado, não faz sentido registrar.
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    # Se o método for POST, o formulário foi enviado
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # --- Verificações de Segurança ---
        if password != confirm_password:
            flash('As senhas não conferem!', 'danger') # 'danger' é uma classe do Bootstrap
            return redirect(url_for('register'))

        user_existente = User.query.filter_by(email=email).first()
        if user_existente:
            flash('Este e-mail já está cadastrado. Tente fazer login.', 'warning')
            return redirect(url_for('register'))
        
        # --- Criar o Usuário ---
        try:
            # Criptografar a senha ANTES de salvar
            senha_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            
            novo_usuario = User(email=email, password_hash=senha_hash)
            
            db.session.add(novo_usuario)
            db.session.commit()
            
            flash('Conta criada com sucesso! Agora você pode fazer o login.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar conta: {e}', 'danger')
            return redirect(url_for('register'))

    # Se o método for GET, apenas mostre a página de registro
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se o usuário já estiver logado, manda para a home
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    # Se o formulário for enviado (POST)
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 1. Encontra o usuário no banco
        user = User.query.filter_by(email=email).first()

        # 2. Verifica se o usuário existe E se a senha está correta
        if user and bcrypt.check_password_hash(user.password_hash, password):
            # 3. Se sim, loga o usuário
            login_user(user)
            
            # (Opcional) Redireciona para a página que ele tentou acessar
            next_page = request.args.get('next')
            flash('Login efetuado com sucesso!', 'success')
            return redirect(next_page or url_for('home'))
        else:
            # 4. Se não, avisa o erro
            flash('E-mail ou senha incorretos. Tente novamente.', 'danger')
            return redirect(url_for('login'))

    # Se for GET, apenas mostra a página de login
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('home'))

# --- ROTAS DA API ---

@app.route('/api/doacoes', methods=['GET'])
def get_doacoes():
    """Rota da API de listagem (não muda)"""
    try:
        doacoes = Doacao.query.all()
        lista_de_doacoes = [d.to_dict() for d in doacoes]
        return jsonify(lista_de_doacoes), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/doacao', methods=['POST'])
@login_required # <-- MÁGICA: Proteger a API também
def create_doacao():
    """Rota da API de criação (MODIFICADA)"""
    try:
        dados = request.get_json() 
        
        nova_doacao = Doacao(
            nome_local=dados['nome_local'],
            itens=dados['itens'],
            horario_retirada=dados['horario_retirada'],
            latitude=dados['latitude'],
            longitude=dados['longitude'],
            author=current_user # <-- MUDANÇA: Associa o usuário logado à doação
        )
        
        db.session.add(nova_doacao)
        db.session.commit()
        return jsonify(nova_doacao.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 400

# --- Execução ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Agora isso também cria a tabela 'user'
    app.run(debug=True)