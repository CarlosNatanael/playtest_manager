from flask import Blueprint, redirect, url_for, session, render_template
from app.models import Game

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role') == 'manager':
        return redirect(url_for('manager.index'))
    else:
        return redirect(url_for('dashboard.index'))
    
import json
from flask import Blueprint, render_template
from app.models import Game, TestSession

public_bp = Blueprint('public', __name__)

@public_bp.route('/cr-board')
def cr_board():
    games = Game.query.filter(Game.status.in_(['In Progress', 'Completed', 'Re-test'])).order_by(Game.created_at.desc()).all()
    return render_template('public/cr.html', games=games)

@public_bp.route('/cr-board/report/<int:session_id>')
def cr_report(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    
    checklist_dict = {}
    if test_session.checklist_data:
        try:
            checklist_dict = json.loads(test_session.checklist_data)
        except:
            pass

    collab_partners = []
    if test_session.game.is_collab:
        collab_partners = TestSession.query.filter(
            TestSession.game_id == test_session.game_id,
            TestSession.id != test_session.id
        ).all()

    return render_template('public/cr_report.html', 
                           test_session=test_session, 
                           checklist=checklist_dict, 
                           results=test_session.results,
                           collab_partners=collab_partners)