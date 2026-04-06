from flask import Blueprint

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    return "Painel do Playtester: testes em andamento."

@dashboard_bp.route('/session/<int:session_id>')
def test_session(session_id):
    return f"Interface de teste para a sessão {session_id}."