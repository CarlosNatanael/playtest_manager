from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from app.models import Game, TestSession, db, TestResult, GameLog, Event
from app.services.ra_api import validate_game_hash
from app.routes.manager import sync_event_progress
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    user_id = session.get('user_id')
    active_event = Event.query.filter_by(is_active=True).first()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    if active_event and 'user_id' in session:
        sync_event_progress(session['user_id'])

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
                           active_game_ids=active_game_ids,
                           active_event=active_event)

@dashboard_bp.before_request
def restrict_dashboard_access():
    if 'username' not in session:
        flash('Please log in to access the system.', 'warning')
        return redirect(url_for('auth.login'))

@dashboard_bp.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    completed_sessions = TestSession.query.filter_by(user_id=user_id, status='Concluded').order_by(TestSession.concluded_at.desc()).all()
    
    return render_template('dashboard/history.html', completed_sessions=completed_sessions)

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

    # Adicionado 'Re-test' para permitir que o tester pegue o jogo novamente
    if game.status not in ['Open', 'Re-test'] and not (game.is_collab and not game.collab_locked):
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

    if test_session.status == 'Concluded':
        return render_template('dashboard/session_view.html', 
                               test_session=test_session, 
                               checklist=checklist_dict,
                               results=test_session.results,
                               collab_partners=collab_partners, 
                               is_owner=is_owner)
    
    return render_template('dashboard/session.html', 
                           test_session=test_session, 
                           results=results_map,
                           checklist=checklist_dict,
                           collab_partners=collab_partners, 
                           is_owner=is_owner)

@dashboard_bp.route('/session/save/<int:session_id>', methods=['POST'])
def save_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    
    # SEGURANÇA: Validar Posse (Ownership)
    if test_session.user_id != session.get('user_id'):
        flash("Access Denied: You cannot modify someone else's session.", "danger")
        return redirect(url_for('dashboard.index'))
        
    data = request.form
    
    test_session.core = data.get('core')
    test_session.hash_used = data.get('hash_used')
    
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
            
        if 'status' in data: 
            new_status = data['status']
            # Guarda o erro original quando o tester marca Retest OK
            if result.trigger_status in ['FALSE_TRIGGER', 'NO_TRIGGER'] and new_status == 'OK_AFTER_RETEST':
                result.previous_status = result.trigger_status
            # Limpa o histórico se trocar de volta para erro (tester errou ao clicar)
            elif new_status in ['FALSE_TRIGGER', 'NO_TRIGGER', 'OK']:
                result.previous_status = None
            result.trigger_status = new_status

            result.notes = data.get(f'note_{ach.id}')
            result.save_state_link = data.get(f'link_{ach.id}')
            
    db.session.commit()
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/session/autosave/<int:session_id>', methods=['POST'])
def autosave(session_id):
    test_session = TestSession.query.get_or_404(session_id) 
    
    # SEGURANÇA: Validar Posse para o Autosave
    if test_session.user_id != session.get('user_id'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
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
        
        if 'status' in data:
            new_status = data['status']
            # Guarda o erro original quando o tester marca Retest OK
            if result.trigger_status in ['FALSE_TRIGGER', 'NO_TRIGGER'] and new_status == 'OK_AFTER_RETEST':
                result.previous_status = result.trigger_status
            # Limpa o histórico se trocar de volta para erro (caso o tester tenha clicado sem querer)
            elif new_status in ['FALSE_TRIGGER', 'NO_TRIGGER', 'OK']:
                result.previous_status = None
                
            result.trigger_status = new_status
        if 'note' in data: result.notes = data['note']
        if 'link' in data: result.save_state_link = data['link']

    if 'checklist_data' in data:
        test_session.checklist_data = data['checklist_data']
    
    db.session.commit()
    return jsonify({"status": "success"})

@dashboard_bp.route('/abandon/<int:session_id>')
def abandon_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    
    # SEGURANÇA: Validar Posse
    if test_session.user_id != session.get('user_id'):
        flash("Unauthorized access. You can only abandon your own tests.", "danger")
        return redirect(url_for('dashboard.index'))
        
    test_session.status = 'Abandoned'
    
    # LÓGICA DE COLLAB: Só volta a 'Open' se não houver mais ninguém testando
    other_active = TestSession.query.filter(
        TestSession.game_id == test_session.game_id,
        TestSession.status == 'Active',
        TestSession.id != test_session.id
    ).first()

    if not other_active:
        test_session.game.status = 'Open'
        
    log = GameLog(game_id=test_session.game_id, username=session.get('username'), action="Abandoned the test")
    db.session.add(log)
    db.session.commit()
    
    flash("You have abandoned the test. The game is back on the Request Board.", "warning")
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/conclude/<int:session_id>')
def conclude_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    
    # SEGURANÇA: Validar Posse
    if test_session.user_id != session.get('user_id'):
        flash("Unauthorized access. You can only conclude your own tests.", "danger")
        return redirect(url_for('dashboard.index'))
        
    test_session.status = 'Concluded'
    test_session.concluded_at = datetime.utcnow() 
    
    # LÓGICA DE COLLAB: Só passa a 'Completed' se todos os outros também já terminaram
    other_active = TestSession.query.filter(
        TestSession.game_id == test_session.game_id,
        TestSession.status == 'Active',
        TestSession.id != test_session.id
    ).first()

    if not other_active:
        test_session.game.status = 'Completed'
        
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
        print(f"ERRO NO VALIDADOR DE HASH: {e}")
        return jsonify({'error': 'An internal error occurred while trying to validate the hash. Please try again later.'}), 500
    
@dashboard_bp.route('/engineer')
def engineer_dashboard():
    if session.get('role') != 'Engineer':
        flash('Access Denied: This area is exclusive to the Bot_Playtest', 'danger')
        if session.get('role') == 'Playtest Manager':
            return redirect(url_for('manager.index'))
        return redirect(url_for('dashboard.index'))
    return render_template('manager/engineer.html')