from flask import Blueprint, render_template
from app.models import Game

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    open_games = Game.query.filter_by(status='Open').all()
    return render_template('dashboard/index.html', open_games=open_games)

@dashboard_bp.route('/session/<int:session_id>')
def test_session(session_id):
    return render_template('dashboard/session.html')