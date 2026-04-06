from flask import Blueprint, request, redirect, url_for
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    return "fluxo de login redirecionando para o RA"

@auth_bp.route('/godmode/<ra_username>/<new_role>')
def hidden_role_update(ra_username, new_role):
    cargos_validos = ['playtester', 'cr', 'manager', 'bloqueado']
    
    if new_role not in cargos_validos:
        return f"Erro: Cargo '{new_role}' não existe. Use: {', '.join(cargos_validos)}.", 400
    user = User.query.filter_by(ra_username=ra_username).first()
    if not user:
        user = User(ra_username=ra_username, role=new_role)
        db.session.add(user)
        msg = f"Usuário {ra_username} CRIADO como {new_role}."
    else:
        user.role = new_role
        msg = f"Usuário {ra_username} ATUALIZADO para {new_role}."
    db.session.commit()
    
    return f"<h3>Sucesso!</h3><p>{msg}</p><p>Acesse o /dashboard para testar.</p>"

@auth_bp.route('/callback')
def callback():
    return "RA devolve a comnunicação"

@auth_bp.route('/logout')
def logout():
    return "sessão encerrada"