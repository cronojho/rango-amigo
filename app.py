import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- Configuração ---
app = Flask(__name__)
CORS(app) 
app.config['SECRET_KEY'] = 'La9QdfPQj0aGUq3RDKRyxdP5suXn3TPEWDMj0olWaN2' # Mantenha sua chave

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DATABASE_URL = os.environ.get('DATABASE_URL') 
if not DATABASE_URL:
    # Use sua URL de fallback local
    DATABASE_URL = "postgresql://rango_amigo_db_user:Fyrzpverx24tmioZRgHKOX8NDwBBEIG4@dpg-d47m05umcj7s73dfsde0-a.oregon-postgres.render.com/rango_amigo_db"
    print("Atenção: Rodando com banco de dados local (fallback).")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info' 

# --- Modelos de Banco de Dados ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    """Modelo de Usuário (com nome_completo)"""
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    doacoes = db.relationship('Doacao', backref='author', lazy=True)

class Doacao(db.Model):
    """Modelo de Doação (com endereço completo)"""
    id = db.Column(db.Integer, primary_key=True)
    nome_local = db.Column(db.String(100), nullable=False)
    itens = db.Column(db.Text, nullable=False)
    horario_retirada = db.Column(db.String(100), nullable=False)
    
    # Coordenadas
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    # Novos Campos de Endereço
    cep = db.Column(db.String(10), nullable=True) 
    rua = db.Column(db.String(200), nullable=True) 
    numero = db.Column(db.String(20), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    
    # Relação com o usuário
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        """Converte o objeto para JSON, incluindo os novos campos"""
        return {
            "id": self.id,
            "nome_local": self.nome_local,
            "itens": self.itens,
            "horario_retirada": self.horario_retirada,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "author_nome": self.author.nome_completo,
            "cep": self.cep,
            "rua": self.rua,
            "numero": self.numero,
            "bairro": self.bairro,
            "cidade": self.cidade
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
    """Rota da página de cadastro de doação"""
    return render_template('postar.html')

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Rota de Registro de Usuário"""
    if current_user.is_authenticated:
        return redirect(url_for('map')) 
    
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
            return redirect(url_for('login')) 
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar conta: {e}', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    """Rota de Login (PÁGINA INICIAL)"""
    if current_user.is_authenticated:
        return redirect(url_for('map')) 

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('map'))
        else:
            flash('E-mail ou senha incorretos. Tente novamente.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login')) 

# --- ROTAS DA API ---

@app.route('/api/doacoes', methods=['GET'])
@login_required 
def get_doacoes():
    """API que lista todas as doações"""
    try:
        doacoes = Doacao.query.all()
        lista_de_doacoes = [d.to_dict() for d in doacoes]
        return jsonify(lista_de_doacoes), 200
    except Exception as e:
        print(f"Erro em get_doacoes: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/api/doacao', methods=['POST'])
@login_required 
def create_doacao():
    """API que cria uma nova doação"""
    try:
        dados = request.get_json() 
        
        nova_doacao = Doacao(
            nome_local=dados['nome_local'],
            itens=dados['itens'],
            horario_retirada=dados['horario_retirada'],
            latitude=dados['latitude'],
            longitude=dados['longitude'],
            
            # Salvando os novos campos de endereço
            cep=dados.get('cep'), 
            rua=dados.get('rua'),
            numero=dados.get('numero'),
            bairro=dados.get('bairro'),
            cidade=dados.get('cidade'),
            
            author=current_user 
        )
        
        db.session.add(nova_doacao)
        db.session.commit()
        return jsonify(nova_doacao.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar doação: {e}") 
        return jsonify({"erro": str(e)}), 400

# --- Execução ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)