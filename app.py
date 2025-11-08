import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# --- Configuração ---
app = Flask(__name__)
CORS(app) 

# --- CONFIGURAÇÃO DO BANCO DE DADOS (A MUDANÇA PRINCIPAL) ---

# COLE A SUA "EXTERNAL CONNECTION URL" DO RENDER AQUI
# IMPORTANTE: Se a sua URL começar com "postgres://", 
# mude para "postgresql://" (o SQLAlchemy exige isso).
DATABASE_URL = "postgresql://rango_amigo_db_user:Fyrzpverx24tmioZRgHKOX8NDwBBEIG4@dpg-d47m05umcj7s73dfsde0-a.oregon-postgres.render.com/rango_amigo_db" 

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- FIM DA MUDANÇA ---

db = SQLAlchemy(app)

# --- Modelo do Banco de Dados (Não muda nada) ---
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

# --- ROTAS DAS PÁGINAS HTML (Não mudam nada) ---

@app.route('/')
def home():
    """Esta rota agora serve a sua página principal (o mapa)"""
    # A primeira vez que rodar no Render, ele cria as tabelas
    with app.app_context():
        db.create_all()
    return render_template('index.html')

@app.route('/postar')
def postar_page():
    """Esta rota serve a sua página de cadastro de doação"""
    return render_template('postar.html')

# --- ROTAS DA API (Não mudam nada) ---

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

# --- Execução (Não muda nada) ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)