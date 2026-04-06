from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    return "fluxo de login redirecionando para o RA"

@auth_bp.route('/callback')
def callback():
    return "RA devolve a comnunicação"

@auth_bp.route('/logout')
def logout():
    return "sessão encerrada"