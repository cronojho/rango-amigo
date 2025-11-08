import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# --- Configuração ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
CORS(app) 

# --- CONFIGURAÇÃO DO BANCO DE DADOS (A MUDANÇA IMPORTANTE) ---
# O Render nos dá um disco persistente em '/var/data'
# Vamos dizer ao app para salvar o BD lá.
db_dir = '/var/data'
db_path = os.path.join(db_dir, 'rango.db')

# Se o diretório '/var/data' não existir (ex: rodando no seu PC),
# salve o BD na pasta local, como antes.
if not os.path.exists(db_dir):
    db_path = os.path.join(basedir, 'rango.db')

print(f"Salvando banco de dados em: {db_path}") # Bom para debug
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- FIM DA MUDANÇA ---

db = SQLAlchemy(app)

# --- Modelo do Banco de Dados ---
class Doacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_local = db.Column(db.String(100), nullable=False)
    itens = db.Column(db.Text, nullable=False)
    horario_retirada = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nome_local": self.nome_local,
            "itens": self.itens,
            "horario_retirada": self.horario_retirada,
            "latitude": self.latitude,
            "longitude": self.longitude
        }

# --- ROTAS DAS PÁGINAS HTML ---

@app.route('/')
def home():
    """Esta rota agora serve a sua página principal (o mapa)"""
    return render_template('index.html')

@app.route('/postar')
def postar_page():
    """Esta rota serve a sua página de cadastro de doação"""
    return render_template('postar.html')

# --- ROTAS DA API (NÃO MUDAM) ---

@app.route('/api/doacoes', methods=['GET'])
def get_doacoes():
    try:
        doacoes = Doacao.query.all()
        lista_de_doacoes = [d.to_dict() for d in doacoes]
        return jsonify(lista_de_doacoes), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/api/doacao', methods=['POST'])
def create_doacao():
    try:
        dados = request.get_json() 
        nova_doacao = Doacao(
            nome_local=dados['nome_local'],
            itens=dados['itens'],
            horario_retirada=dados['horario_retirada'],
            latitude=dados['latitude'],
            longitude=dados['longitude']
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
    # O Gunicorn vai rodar o app, esta linha é só para testes locais
    app.run(debug=True)