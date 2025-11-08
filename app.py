import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# --- Configuração ---
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
# Permite que o front-end (de qualquer origem) acesse esta API
CORS(app) 

# Configura o banco de dados SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'rango.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Modelo do Banco de Dados ---
# Esta é a sua "tabela" de doações
class Doacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_local = db.Column(db.String(100), nullable=False)
    itens = db.Column(db.Text, nullable=False)
    horario_retirada = db.Column(db.String(100), nullable=False)
    # --- CAMPOS NOVOS ---
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    def to_dict(self):
        """Converte o objeto Doacao para um dicionário (para enviar como JSON)"""
        return {
            "id": self.id,
            "nome_local": self.nome_local,
            "itens": self.itens,
            "horario_retirada": self.horario_retirada,
            # --- CAMPOS NOVOS ---
            "latitude": self.latitude,
            "longitude": self.longitude
        }

# --- Rotas da API (Os "Endereços" do seu Cérebro) ---

@app.route('/')
def home():
    return "API do Rango Amigo está no ar!"

# ROTA 1: Obter TODAS as doações (para o Feed)
@app.route('/api/doacoes', methods=['GET'])
def get_doacoes():
    try:
        doacoes = Doacao.query.all()
        # Converte a lista de doações para uma lista de dicionários
        lista_de_doacoes = [d.to_dict() for d in doacoes]
        return jsonify(lista_de_doacoes), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ROTA 2: Criar UMA nova doação (pelo Formulário)
@app.route('/api/doacao', methods=['POST'])
def create_doacao():
    try:
        dados = request.get_json() # Pega os dados que o front-end enviar (em JSON)

        # --- CORREÇÃO ESTÁ AQUI ---
        nova_doacao = Doacao(
            nome_local=dados['nome_local'],
            itens=dados['itens'],
            horario_retirada=dados['horario_retirada'],
            # Linhas que estavam faltando:
            latitude=dados['latitude'],
            longitude=dados['longitude']
        )
        # --- FIM DA CORREÇÃO ---
        
        db.session.add(nova_doacao)
        db.session.commit()
        
        return jsonify(nova_doacao.to_dict()), 201 # 201 = "Criado com Sucesso"
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 400 # 400 = "Erro do usuário"

# --- Execução ---
if __name__ == '__main__':
    # Cria o banco de dados (o arquivo rango.db) se ele não existir
    with app.app_context():
        db.create_all()
    
    app.run(debug=True) # Inicia o servidor