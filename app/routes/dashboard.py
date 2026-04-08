from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from app.models import Game, TestSession, db, TestResult, GameLog
from app.services.ra_api import validate_game_hash
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    open_games = Game.query.filter(
        db.or_(
            Game.status == 'Open',
            db.and_(Game.status == 'In Progress', Game.is_collab == True, Game.collab_locked == False)
        )
    ).all()
    active_sessions = TestSession.query.filter_by(user_id=user_id, status='Active').all()
    active_game_ids = [s.game_id for s in active_sessions]
    
    return render_template('dashboard/index.html', 
                           open_games=open_games, 
                           active_sessions=active_sessions,
                           active_game_ids=active_game_ids)

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

    existing = TestSession.query.filter_by(user_id=user_id, game_id=game.id, status='Active').first()
    if existing:
        flash("You are already testing this game!", "info")
        return redirect(url_for('dashboard.test_session', session_id=existing.id))
    
    active_count = TestSession.query.filter_by(game_id=game.id, status='Active').count()
    if game.is_collab and active_count >= 4:
        flash("This Collab has reached its maximum capacity (4 Testers).", "warning")
        return redirect(url_for('dashboard.index'))

    if game.status != 'Open' and not (game.is_collab and not game.collab_locked):
        flash("This test is currently closed to new participants.", "warning")
        return redirect(url_for('dashboard.index'))
    

    new_session = TestSession(
        user_id=user_id,
        game_id=game.id,
        status='Active',
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    game.status = 'In Progress'

    log = GameLog(game_id=game.id, username=session.get('username'), action="Claimed the game for testing")
    db.session.add(log)
    
    db.session.add(new_session)
    db.session.commit()
    
    flash(f"You have started testing {game.title}!", "success")
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

    collab_partners = []
    if test_session.game.is_collab:
        collab_partners = TestSession.query.filter(
            TestSession.game_id == test_session.game_id,
            TestSession.id != test_session.id
        ).all()

    first_session = TestSession.query.filter_by(game_id=test_session.game_id).order_by(TestSession.id.asc()).first()
    is_owner = first_session and (first_session.user_id == session.get('user_id'))

    return render_template('dashboard/session.html',
                           test_session=test_session,
                           results=results_map, 
                           checklist=checklist_dict,
                           collab_partners=collab_partners,
                           is_owner=is_owner)

@dashboard_bp.route('/session/save/<int:session_id>', methods=['POST'])
def save_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    data = request.form
    
    # Save header data
    test_session.core = data.get('core')
    test_session.hash_used = data.get('hash_used')
    
    # Process each achievement
    for ach in test_session.game.achievements:
        status = data.get(f'ach_{ach.id}')
        if status:
            result = TestResult.query.filter_by(
                session_id=test_session.id, 
                achievement_id=ach.id
            ).first()
            
            if not result:
                result = TestResult(session_id=test_session.id, achievement_id=ach.id)
                db.session.add(result)
            
            result.trigger_status = status
            result.notes = data.get(f'note_{ach.id}')
            result.save_state_link = data.get(f'link_{ach.id}')
            
    db.session.commit()
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/session/autosave/<int:session_id>', methods=['POST'])
def autosave(session_id):
    test_session = TestSession.query.get_or_404(session_id) 
    data = request.json
    
    if 'emulator' in data: test_session.emulator = data['emulator']
    if 'core' in data: test_session.core = data['core']
    if 'hash_used' in data: test_session.hash_used = data['hash_used']
    if 'set_impressions' in data: test_session.set_impressions = data['set_impressions']
    if 'collab_locked' in data: test_session.game.collab_locked = data['collab_locked']
    
    if 'is_collab' in data: 
        test_session.is_collab = data['is_collab']
        test_session.game.is_collab = data['is_collab'] 
    
    if 'achievement_id' in data:
        ach_id = data['achievement_id']
        result = TestResult.query.filter_by(session_id=test_session.id, achievement_id=ach_id).first()
        
        if not result:
            result = TestResult(session_id=test_session.id, achievement_id=ach_id)
            db.session.add(result)
        
        if 'status' in data: result.trigger_status = data['status']
        if 'note' in data: result.notes = data['note']
        if 'link' in data: result.save_state_link = data['link']

    if 'checklist_data' in data:
        test_session.checklist_data = data['checklist_data']
    
    db.session.commit()
    return jsonify({"status": "success"})

@dashboard_bp.route('/abandon/<int:session_id>')
def abandon_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    test_session.status = 'Abandoned'
    test_session.game.status = 'Open'
    log = GameLog(game_id=test_session.game_id, username=session.get('username'), action="Abandoned the test")
    db.session.add(log)
    db.session.commit() # Adicionei o commit aqui que faltava no original
    
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

@dashboard_bp.route('/session/validate_hash/<int:session_id>', methods=['POST'])
def validate_hash(session_id):
    try:
        test_session = TestSession.query.get_or_404(session_id)
        data = request.json
        hash_to_check = data.get('hash', '')
        
        if not hash_to_check:
            return jsonify({'valid': False, 'empty': True})
            
        is_valid = validate_game_hash(test_session.game_id, hash_to_check)
        return jsonify({'valid': is_valid, 'empty': False})
    except Exception as e:
        print(f"ERRO NO VALIDADOR DE HASH: {e}") # Vai aparecer no seu terminal!
        return jsonify({'error': str(e)}), 500