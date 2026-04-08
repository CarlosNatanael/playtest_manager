from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from app.models import Game, TestSession, db, TestResult
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    open_games = Game.query.filter_by(status='Open').all()
    active_sessions = TestSession.query.filter_by(user_id=1, status='Active').all()
    
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
    results_map = {r.achievement_id: r for r in session.results}

    checklist_dict = {}
    if session.checklist_data:
        try:
            checklist_dict = json.loads(session.checklist_data)
        except:
            pass

    return render_template('dashboard/session.html', 
                           session=session, 
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
    session = TestSession.query.get_or_404(session_id)
    session.status = 'Abandoned'
    session.game.status = 'Open' # Libera o jogo para outros
    db.session.commit()
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/conclude/<int:session_id>')
def conclude_session(session_id):
    session = TestSession.query.get_or_404(session_id)
    session.status = 'Concluded'
    session.game.status = 'Completed'
    db.session.commit()
    return redirect(url_for('dashboard.index'))