import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- Configuração (sem alteração) ---
app = Flask(__name__)
CORS(app) 
app.config['SECRET_KEY'] = 'La9QdfPQj0aGUq3RDKRyxdP5suXn3TPEWDMj0olWaN2' 

# --- CONFIGURAÇÃO DO BANCO DE DADOS (sem alteração) ---
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
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info' 

# --- Modelos de Banco de Dados ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    # (Modelo User sem alteração)
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    doacoes = db.relationship('Doacao', backref='author', lazy=True)

class Doacao(db.Model):
    """Modelo de Doação (com campo 'is_archived')"""
    id = db.Column(db.Integer, primary_key=True)
    nome_local = db.Column(db.String(100), nullable=False)
    itens = db.Column(db.Text, nullable=False)
    horario_retirada = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    cep = db.Column(db.String(10), nullable=True) 
    rua = db.Column(db.String(200), nullable=True) 
    numero = db.Column(db.String(20), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # === CAMPO NOVO ===
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        """Converte o objeto para JSON, incluindo o status de arquivado"""
        return {
            "id": self.id,
            "nome_local": self.nome_local,
            "itens": self.itens,
            "horario_retirada": self.horario_retirada,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "author_nome": self.author.nome_completo,
            "user_id": self.user_id, 
            "cep": self.cep,
            "rua": self.rua,
            "numero": self.numero,
            "bairro": self.bairro,
            "cidade": self.cidade,
            "is_archived": self.is_archived # <-- NOVO
        }

# --- ROTAS DAS PÁGINAS HTML ---

@app.route('/map')
@login_required 
def map():
    return render_template('index.html')

@app.route('/postar')
@login_required 
def postar_page():
    return render_template('postar.html')

# === ROTA NOVA ===
@app.route('/minhas-doacoes')
@login_required
def minhas_doacoes_page():
    """Página para o usuário gerenciar suas doações (ativas e arquivadas)"""
    return render_template('minhas-doacoes.html')

# --- ROTAS DE AUTENTICAÇÃO (sem alteração) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    # (código sem alteração)
    if current_user.is_authenticated:
        return redirect(url_for('map')) 
    if request.method == 'POST':
        # ... (lógica de registro) ...
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
            novo_usuario = User(nome_completo=nome_completo, email=email, password_hash=senha_hash)
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
    # (código sem alteração)
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
    # (código sem alteração)
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login')) 

# --- ROTAS DA API ---

@app.route('/api/doacoes', methods=['GET'])
@login_required 
def get_doacoes():
    """API que lista apenas doações ATIVAS (para o mapa)"""
    try:
        # === MUDANÇA AQUI ===
        # Filtra apenas as doações que NÃO estão arquivadas
        doacoes = Doacao.query.filter_by(is_archived=False).all()
        lista_de_doacoes = [d.to_dict() for d in doacoes]
        return jsonify(lista_de_doacoes), 200
    except Exception as e:
        print(f"Erro em get_doacoes: {e}")
        return jsonify({"erro": str(e)}), 500

# === ROTA NOVA ===
@app.route('/api/doacoes/minhas', methods=['GET'])
@login_required
def get_minhas_doacoes():
    """API que lista TODAS as doações (ativas e arquivadas) do usuário logado"""
    try:
        doacoes = Doacao.query.filter_by(author=current_user).order_by(Doacao.is_archived, Doacao.id.desc()).all()
        lista_de_doacoes = [d.to_dict() for d in doacoes]
        return jsonify(lista_de_doacoes), 200
    except Exception as e:
        print(f"Erro em get_minhas_doacoes: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/api/doacao', methods=['POST'])
@login_required 
def create_doacao():
    # (Função create_doacao sem alteração)
    try:
        dados = request.get_json() 
        nova_doacao = Doacao(
            nome_local=dados['nome_local'],
            itens=dados['itens'],
            horario_retirada=dados['horario_retirada'],
            latitude=dados['latitude'],
            longitude=dados['longitude'],
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

# === ROTA DE EXCLUSÃO (LÓGICA ATUALIZADA) ===
@app.route('/api/doacao/<int:doacao_id>', methods=['DELETE'])
@login_required
def delete_doacao(doacao_id):
    """API que exclui uma doação (PERMANENTEMENTE)"""
    try:
        doacao = Doacao.query.get(doacao_id)
        if not doacao:
            return jsonify({"erro": "Doação não encontrada"}), 404
            
        if doacao.author.id != current_user.id:
            return jsonify({"erro": "Você não tem permissão para excluir esta doação"}), 403
            
        # === MUDANÇA: SÓ PODE EXCLUIR SE ESTIVER ARQUIVADO ===
        if not doacao.is_archived:
            return jsonify({"erro": "Você só pode excluir doações que já estão arquivadas."}), 400
            
        db.session.delete(doacao)
        db.session.commit()
        
        return jsonify({"message": "Doação excluída permanentemente"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao excluir doação: {e}")
        return jsonify({"erro": str(e)}), 500

# === ROTA NOVA (ARQUIVAR) ===
@app.route('/api/doacao/archive/<int:doacao_id>', methods=['PATCH'])
@login_required
def archive_doacao(doacao_id):
    """API que ARQUIVA uma doação (muda is_archived para True)"""
    try:
        doacao = Doacao.query.get(doacao_id)
        if not doacao:
            return jsonify({"erro": "Doação não encontrada"}), 404
        if doacao.author.id != current_user.id:
            return jsonify({"erro": "Não autorizado"}), 403
            
        doacao.is_archived = True
        db.session.commit()
        return jsonify({"message": "Doação arquivada com sucesso"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500

# === ROTA NOVA (RESTAURAR) ===
@app.route('/api/doacao/restore/<int:doacao_id>', methods=['PATCH'])
@login_required
def restore_doacao(doacao_id):
    """API que RESTAURA uma doação (muda is_archived para False)"""
    try:
        doacao = Doacao.query.get(doacao_id)
        if not doacao:
            return jsonify({"erro": "Doação não encontrada"}), 404
        if doacao.author.id != current_user.id:
            return jsonify({"erro": "Não autorizado"}), 403
            
        doacao.is_archived = False
        db.session.commit()
        return jsonify({"message": "Doação restaurada com sucesso"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500

# --- Execução (sem alteração) ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)