from flask import Blueprint, render_template, redirect, url_for, flash
from app.models import Game, TestSession, db
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    open_games = Game.query.filter_by(status='Open').all()
    active_sessions = TestSession.query.filter_by(user_id=1, status='Active').all()
    
    return render_template('dashboard/index.html', 
                           open_games=open_games, 
                           active_sessions=active_sessions)

@dashboard_bp.route('/claim/<int:game_id>')
def claim_game(game_id):
    game = Game.query.get_or_404(game_id)
    if game.status != 'Open':
        flash("Este jogo já foi reivindicado por outro tester.", "warning")
        return redirect(url_for('dashboard.index'))
    new_session = TestSession(
        user_id=1,
        game_id=game.id,
        status='Active',
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    game.status = 'In Progress'
    db.session.add(new_session)
    db.session.commit()
    
    flash(f"Você iniciou o teste de {game.title}!", "success")
    return redirect(url_for('dashboard.test_session', session_id=new_session.id))

@dashboard_bp.route('/session/<int:session_id>')
def test_session(session_id):
    session = TestSession.query.get_or_404(session_id)
    results = {r.achievement_id: r for r in session.results}
    return render_template('dashboard/session.html', session=session, results=results)