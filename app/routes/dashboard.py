from flask import Blueprint, render_template

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    return render_template('dashboard/index.html')

@dashboard_bp.route('/session/<int:session_id>')
def test_session(session_id):
    return f"Interface de teste para a sessão {session_id}."