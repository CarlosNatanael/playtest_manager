from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from app.models import Game, TestSession, db, TestResult, GameLog
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    open_games = Game.query.filter_by(status='Open').all()
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
        
    active_sessions = TestSession.query.filter_by(user_id=user_id, status='Active').all()
    
    return render_template('dashboard/index.html', 
                           open_games=open_games, 
                           active_sessions=active_sessions)

@dashboard_bp.route('/view_game/<int:game_id>')
def view_game(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('dashboard/view_game.html', game=game)

@dashboard_bp.route('/claim/<int:game_id>')
def claim_game(game_id):
    game = Game.query.get_or_404(game_id)

    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to claim a game.", "danger")
        return redirect(url_for('auth.login'))

    if game.status != 'Open':
        flash("This game has already been claimed by another tester.", "warning")
        return redirect(url_for('dashboard.index'))
    new_session = TestSession(
        user_id=user_id,
        game_id=game.id,
        status='Active',
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    game.status = 'In Progress'
    db.session.add(new_session)
    log = GameLog(game_id=game.id, username=session.get('username'), action="Claimed the game for testing")
    db.session.add(log)
    db.session.commit()
    
    flash(f"You have started the {game.title} test!", "success")
    return redirect(url_for('dashboard.test_session', session_id=new_session.id))

@dashboard_bp.route('/session/<int:session_id>')
def test_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    results_map = {r.achievement_id: r for r in test_session.results}

    checklist_dict = {}
    if test_session.checklist_data:
        try:
            checklist_dict = json.loads(test_session.checklist_data)
        except:
            pass

    return render_template('dashboard/session.html', 
                           test_session=test_session,
                           results=results_map, 
                           checklist=checklist_dict)

@dashboard_bp.route('/session/save/<int:session_id>', methods=['POST'])
def save_session(session_id):
    session = TestSession.query.get_or_404(session_id)
    data = request.form
    
    # Salva dados do cabeçalho
    session.core = data.get('core')
    session.hash_used = data.get('hash_used')
    
    # Processa cada conquista
    for ach in session.game.achievements:
        status = data.get(f'ach_{ach.id}')
        if status:
            # Busca resultado existente ou cria novo
            result = TestResult.query.filter_by(
                session_id=session.id, 
                achievement_id=ach.id
            ).first()
            
            if not result:
                result = TestResult(session_id=session.id, achievement_id=ach.id)
                db.session.add(result)
            
            result.trigger_status = status
            result.notes = data.get(f'note_{ach.id}')
            result.save_state_link = data.get(f'link_{ach.id}')
            
    db.session.commit()
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/session/autosave/<int:session_id>', methods=['POST'])
def autosave(session_id):
    session = TestSession.query.get_or_404(session_id)
    data = request.json
    
    # Atualiza dados globais da sessão
    if 'emulator' in data: session.emulator = data['emulator']
    if 'core' in data: session.core = data['core']
    if 'hash_used' in data: session.hash_used = data['hash_used']
    if 'is_collab' in data: session.is_collab = data['is_collab']
    if 'set_impressions' in data: session.set_impressions = data['set_impressions']
    
    # Atualiza ou cria o resultado de uma conquista específica
    if 'achievement_id' in data:
        ach_id = data['achievement_id']
        result = TestResult.query.filter_by(session_id=session.id, achievement_id=ach_id).first()
        
        if not result:
            result = TestResult(session_id=session.id, achievement_id=ach_id)
            db.session.add(result)
        
        if 'status' in data: result.trigger_status = data['status']
        if 'note' in data: result.notes = data['note']
        if 'link' in data: result.save_state_link = data['link']

    if 'checklist_data' in data:
        session.checklist_data = data['checklist_data']
    
    db.session.commit()
    return jsonify({"status": "success"})

@dashboard_bp.route('/abandon/<int:session_id>')
def abandon_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    test_session.status = 'Abandoned'
    test_session.game.status = 'Open' # Libera o jogo para outros
    log = GameLog(game_id=test_session.game_id, username=session.get('username'), action="Abandoned the test")
    db.session.add(log)
    
    flash("You have abandoned the test. The game is back on the Request Board.", "warning")
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/conclude/<int:session_id>')
def conclude_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    test_session.status = 'Concluded'
    test_session.game.status = 'Completed'
    test_session.concluded_at = datetime.utcnow() 
    log = GameLog(game_id=test_session.game_id, username=session.get('username'), action="Concluded the test and submitted report")
    db.session.add(log)
    db.session.commit()
    
    flash("Test successfully concluded! The report was sent to the Manager.", "success")
    return redirect(url_for('dashboard.index'))