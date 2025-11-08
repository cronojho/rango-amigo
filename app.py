import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- Configuração ---
app = Flask(__name__)
CORS(app) 
app.config['SECRET_KEY'] = 'La9QdfPQj0aGUq3RDKRyxdP5suXn3TPEWDMj0olWaN2'

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DATABASE_URL = os.environ.get('DATABASE_URL') 
if not DATABASE_URL:
    DATABASE_URL = "postgresql://rango_amigo_db_user:Fyrzpverx24tmioZRgHKOX8NDwBBEIG4@dpg-d47m05umcj7s73dfsde0-a.oregon-postgres.render.com/rango_amigo_db"
    print("Atenção: Rodando com banco de dados local (fallback).")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
# --- MUDANÇA: A ROTA DE LOGIN AGORA SE CHAMA 'login' ---
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info' 

# --- Modelos de Banco de Dados ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    doacoes = db.relationship('Doacao', backref='author', lazy=True)

class Doacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_local = db.Column(db.String(100), nullable=False)
    itens = db.Column(db.Text, nullable=False)
    horario_retirada = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nome_local": self.nome_local,
            "itens": self.itens,
            "horario_retirada": self.horario_retirada,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "author_nome": self.author.nome_completo 
        }

# --- ROTAS DAS PÁGINAS HTML ---

@app.route('/map')
@login_required # O mapa agora é protegido
def map():
    """Rota do Mapa"""
    return render_template('index.html')

@app.route('/postar')
@login_required 
def postar_page():
    """Rota da página de cadastro"""
    return render_template('postar.html')

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Função de Registro (MODIFICADA)"""
    if current_user.is_authenticated:
        return redirect(url_for('map')) # Se já logado, vai pro mapa
    
    if request.method == 'POST':
        nome_completo = request.form.get('nome_completo')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('As senhas não conferem!', 'danger') 
            return redirect(url_for('register'))

        user_existente = User.query.filter_by(email=email).first()
        if user_existente:
            flash('Este e-mail já está cadastrado. Tente fazer login.', 'warning')
            return redirect(url_for('register'))
        
        try:
            senha_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            novo_usuario = User(
                nome_completo=nome_completo, 
                email=email, 
                password_hash=senha_hash
            )
            db.session.add(novo_usuario)
            db.session.commit()
            
            flash('Conta criada com sucesso! Agora você pode fazer o login.', 'success')
            return redirect(url_for('login')) # Redireciona para o login
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar conta: {e}', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    """Rota de Login (AGORA É A PÁGINA INICIAL)"""
    if current_user.is_authenticated:
        return redirect(url_for('map')) # Se já logado, vai pro mapa

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            # Redireciona para o mapa!
            return redirect(url_for('map'))
        else:
            flash('E-mail ou senha incorretos. Tente novamente.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login')) # Redireciona para o login

# --- ROTAS DA API ---

@app.route('/api/doacoes', methods=['GET'])
@login_required # Protege a API também
def get_doacoes():
    try:
        doacoes = Doacao.query.all()
        lista_de_doacoes = [d.to_dict() for d in doacoes]
        return jsonify(lista_de_doacoes), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/doacao', methods=['POST'])
@login_required 
def create_doacao():
    try:
        dados = request.get_json() 
        nova_doacao = Doacao(
            nome_local=dados['nome_local'],
            itens=dados['itens'],
            horario_retirada=dados['horario_retirada'],
            latitude=dados['latitude'],
            longitude=dados['longitude'],
            author=current_user 
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
        db.create_all() 
    app.run(debug=True)