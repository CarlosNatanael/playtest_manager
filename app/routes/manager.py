from app.models import Game, Achievement, TestSession, TestResult, User, GameLog, Event, EventChallenge, UserEventProgress
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.ra_api import get_developer_level, fetch_game_and_achievements
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask import current_app
from PIL import Image
from app import db
import secrets
import json
import uuid
import os

manager_bp = Blueprint('manager', __name__)

def get_allowed_users_path():
    return os.path.join(current_app.instance_path, 'allowed_users.json')

@manager_bp.route('/team', methods=['GET', 'POST'])
def manage_team():
    file_path = get_allowed_users_path()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
    except FileNotFoundError:
        users_db = {}

    if request.method == 'POST':
        form_username = request.form.get('username') 
        role = request.form.get('role')
        creation_method = request.form.get('creation_method') 

        if User.query.filter_by(ra_username=form_username).first():
            flash(f"User '{form_username}' already exists.", "danger")
        else:
            new_user = User(ra_username=form_username, role=role)
            
            if creation_method == 'link':
                token = secrets.token_urlsafe(32)
                new_user.password_hash = 'PENDING_INVITE'
                new_user.invite_token = token
                new_user.token_expiry = datetime.utcnow() + timedelta(hours=24)
                
                db.session.add(new_user)
                db.session.commit()
                
                invite_url = url_for('auth.setup_password', token=token, _external=True)
                
                flash(f"User created! Copy the link below and send it to them (Valid for 24h):<br><input type='text' class='form-control bg-dark text-info mt-2' value='{invite_url}' readonly onclick='this.select()'>", "success")
            
            else:
                # MANUAL CREATION
                password = request.form.get('password')
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash(f"User '{form_username}' added successfully with manual password.", "success")
                
        return redirect(url_for('manager.manage_team'))

    users = User.query.all()
    return render_template('manager/team.html', users=users, users_db=users_db)

@manager_bp.route('/team/delete/<username>', methods=['POST'])
def delete_user(username):
    user = User.query.filter_by(ra_username=username).first()
    
    if user:
        if user.ra_username == session.get('username'):
            flash("You cannot revoke your own access!", "warning")
        else:
            user.is_active = False 
            user.password_hash = None
            user.invite_token = None
            
            db.session.commit()
            flash(f"Access for {username} revoked! Test history has been preserved in the system.", "success")
    else:
        flash(f"User {username} not found.", "danger")
        
    return redirect(url_for('manager.manage_team'))

@manager_bp.route('/team/restore/<username>', methods=['POST'])
def restore_user(username):
    user = User.query.filter_by(ra_username=username).first()
    
    if user:
        user.is_active = True
        db.session.commit()
        flash(f"Access for {username} restored! You can generate a new magic link or password for them using the form.", "success")
    else:
        flash(f"User {username} not found.", "danger")
        
    return redirect(url_for('manager.manage_team'))

@manager_bp.route('/')
def index():
    games = Game.query.filter(Game.status.in_(['Open', 'In Progress', 'Re-test'])).all()
    active_sessions = TestSession.query.filter_by(status='Active').all()
    
    active_sessions_map = {s.game_id: s for s in active_sessions}

    return render_template('manager/index.html', 
                           games=games, 
                           active_sessions_map=active_sessions_map, 
                           now=datetime.utcnow())

@manager_bp.route('/engineer')
def engineer_dashboard():
    if session.get('role') != 'Engineer':
        flash('Access Denied: This area is exclusive to the Bot_Playtest', 'danger')
        if session.get('role') == 'Playtest Manager':
            return redirect(url_for('manager.index'))
        return redirect(url_for('dashboard.index'))
    return render_template('manager/engineer.html')

@manager_bp.route('/history')
def history():
    games = Game.query.filter_by(status='Completed').all()
    # Fetches ALL concluded sessions, grouped by game_id
    concluded_sessions = TestSession.query.filter_by(status='Concluded').all()
    # Groups as a list, does not overwrite
    sessions_map = {}
    for s in concluded_sessions:
        if s.game_id not in sessions_map:
            sessions_map[s.game_id] = []
        sessions_map[s.game_id].append(s)

    return render_template('manager/history.html', 
                           games=games, 
                           sessions_map=sessions_map, 
                           now=datetime.utcnow())

@manager_bp.route('/review/<int:session_id>')
def review_session(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    results = TestResult.query.filter_by(session_id=session_id).all()

    from app.models import GameLog
    game_logs = GameLog.query.filter_by(game_id=test_session.game_id).order_by(GameLog.timestamp.desc()).all()
    
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

    return render_template('manager/session_view.html', 
                           test_session=test_session,
                           results=results,
                           checklist=checklist_dict,
                           logs=game_logs,
                           collab_partners=collab_partners)

@manager_bp.route('/import', methods=['GET', 'POST'])
def import_game():
    if request.method == 'POST':
        game_id = request.form.get('game_id')
        if not game_id:
            flash('Please enter a Game ID.', 'warning')
            return redirect(url_for('manager.import_game'))
            
        existing = Game.query.get(game_id)
        if existing:
            flash('This game has already been imported!', 'info')
            return redirect(url_for('manager.index'))

        game_data, erro = fetch_game_and_achievements(game_id)
        
        if erro or not game_data:
            flash(f"Import error: {erro or 'Empty data'}", 'danger')
            return redirect(url_for('manager.import_game'))

        developer_name = game_data.get('developer', 'Unknown')
        dev_level_automatico = get_developer_level(developer_name)

        new_game = Game(
            id=game_data['id'],
            title=game_data.get('title', 'Unknown'),
            developer=developer_name,
            developer_level=dev_level_automatico,
            developer_pic=game_data.get('developer_pic', ''),
            console_name=game_data.get('console_name', 'Unknown'),
            image_icon=game_data.get('image_icon', ''),
            is_collab=game_data.get('is_collab', False)
        )
        
        db.session.add(new_game)
        
        achievements_list = game_data.get('achievements', [])
        for ach in achievements_list:
            new_ach = Achievement(
                id=ach['id'],
                game_id=new_game.id,
                title=ach.get('title', 'Unknown'),
                description=ach.get('description', ''),
                badge_name=ach.get('badge_name', ''),
                points=ach.get('points', 0)
            )
            db.session.add(new_ach)

        log = GameLog(game_id=new_game.id, username=session.get('username'), action="Imported the game for playtesting")
        db.session.add(log)

        db.session.commit()
        flash(f"Game '{new_game.title}' imported successfully! Level detected: {dev_level_automatico}", "success")
        return redirect(url_for('manager.index'))

    return render_template('manager/import.html')


@manager_bp.route('/stats')
def tester_stats():
    testers = User.query.all()
    stats_data = []
    
    for tester in testers:
        sessions = TestSession.query.filter_by(user_id=tester.id).all()
        
        reports_submitted = len([s for s in sessions if s.status == 'Concluded'])
        
        validated_achs = TestResult.query.join(TestSession).filter(
            TestSession.user_id == tester.id,
            TestResult.trigger_status.in_(['OK', 'OK_AFTER_RETEST'])
        ).count()
        
        issues_found = TestResult.query.join(TestSession).filter(
            TestSession.user_id == tester.id,
            TestResult.trigger_status.in_(['FALSE_TRIGGER', 'NO_TRIGGER', 'OK_AFTER_RETEST'])
        ).count()

        enriched_sessions = []
        for s in sessions:
            val = sum(1 for r in s.results if r.trigger_status in ['OK', 'OK_AFTER_RETEST'])
            iss = sum(1 for r in s.results if r.trigger_status in ['FALSE_TRIGGER', 'NO_TRIGGER', 'OK_AFTER_RETEST'])
            tested = val + iss
            
            fields_filled = 0
            if s.emulator: fields_filled += 1
            if s.core: fields_filled += 1
            if s.hash_used: fields_filled += 1
            if s.set_impressions: fields_filled += 1

            if s.checklist_data:
                try:
                    chk = json.loads(s.checklist_data)
                    fields_filled += sum(1 for k, v in chk.items() if v)
                except:
                    pass
                    
            enriched_sessions.append({
                'obj': s,
                'val': val,
                'iss': iss,
                'tested': tested,
                'fields': fields_filled
            })
        
        stats_data.append({
            'username': tester.ra_username,
            'reports': reports_submitted,
            'validated': validated_achs,
            'issues': issues_found,
            'sessions': enriched_sessions
        })
        
    stats_data.sort(key=lambda x: x['reports'], reverse=True)

    return render_template('manager/stats.html', stats_data=stats_data)

@manager_bp.route('/delete/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)
    title = game.title
    db.session.delete(game)
    db.session.commit()
    flash(f"Game '{title}' has been removed from the database.", "success")
    return redirect(url_for('manager.index'))

@manager_bp.before_request
def restrict_manager_access():
    if 'username' not in session:
        flash('Please log in to access this area.', 'warning')
        return redirect(url_for('auth.login'))
    
    allowed_roles = ['Playtest Manager', 'Engineer']
    if session.get('role') not in allowed_roles:
        flash('Access Denied: You do not have Manager permissions.', 'danger')
        return redirect(url_for('dashboard.index'))
    
@manager_bp.route('/reopen_retest/<int:game_id>', methods=['POST'])
def reopen_retest(game_id):
    game = Game.query.get_or_404(game_id)
    game.status = 'Re-test'
    db.session.commit()
    flash(f"Game '{game.title}' is now back on the Request Board for a second test.", "success")
    return redirect(url_for('manager.history'))

@manager_bp.route('/team/reset/<username>', methods=['POST'])
def reset_password(username):
    user = User.query.filter_by(ra_username=username).first()
    
    if user:
        import secrets
        from datetime import datetime, timedelta
        
        token = secrets.token_urlsafe(32)
        user.invite_token = token
        user.token_expiry = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        
        invite_url = url_for('auth.setup_password', token=token, _external=True)
        
        flash(f"Recovery link generated for <b>{username}</b>! Copy and send via DM:<br><input type='text' class='form-control bg-dark text-info mt-2' value='{invite_url}' readonly onclick='this.select()'>", "success")
    else:
        flash(f"User {username} not found.", "danger")
        
    return redirect(url_for('manager.manage_team'))

@manager_bp.route('/team/edit_image/<username>', methods=['POST'])
def edit_image_name(username):
    user = User.query.filter_by(ra_username=username).first()
    
    if user:
        old_name = request.form.get('old_name')
        user.image_username = old_name if old_name else None
        db.session.commit()
        
        if username == session.get('username'):
            session['image_username'] = user.image_username
            
        flash(f"Photo name updated to {username}!", "success")
    
    return redirect(url_for('manager.manage_team'))

# ROTAS DO SISTEMA DE EVENTOS

@manager_bp.route('/events', methods=['GET', 'POST'])
def manage_events():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        badge_url = request.form.get('badge_url')
        
        new_event = Event(title=title, description=description, badge_url=badge_url)
        db.session.add(new_event)
        db.session.commit()
        flash(f"Event '{title}' created successfully!", "success")
        return redirect(url_for('manager.manage_events'))
        
    events = Event.query.order_by(Event.start_date.desc()).all()
    active_event = Event.query.filter_by(is_active=True).first()
    pending_approvals = []
    
    if active_event:
        # Busca progressos de desafios MANUAIS que ainda NÃO estão completos
        pending_approvals = UserEventProgress.query.join(EventChallenge).filter(
            EventChallenge.event_id == active_event.id,
            EventChallenge.challenge_type == 'manual',
            UserEventProgress.is_completed == False
        ).all()

    return render_template('manager/events.html', 
                           events=events, 
                           pending_approvals=pending_approvals)

@manager_bp.route('/events/<int:event_id>/toggle', methods=['POST'])
def toggle_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if not event.is_active:
        Event.query.update({Event.is_active: False})
        
    event.is_active = not event.is_active
    db.session.commit()
    
    status = "activated" if event.is_active else "deactivated"
    flash(f"Event '{event.title}' has been {status}.", "info")
    return redirect(url_for('manager.manage_events'))

@manager_bp.route('/events/manual_approve/<int:progress_id>', methods=['POST'])
def approve_manual_challenge(progress_id):
    
    progress = UserEventProgress.query.get_or_404(progress_id)
    progress.current_value = progress.challenge.target_value
    progress.is_completed = True
    progress.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f"Challenge approved for {progress.tester_progress.ra_username}!", "success")
    return redirect(url_for('manager.manage_events'))

@manager_bp.route('/events/<int:event_id>/challenge', methods=['POST'])
def add_challenge(event_id):
    event = Event.query.get_or_404(event_id)
    
    badge_file = request.files.get('badge_file')
    badge_url = request.form.get('badge_url')
    
    final_badge_path = None
    if badge_file and badge_file.filename != '':
        final_badge_path = save_and_compress_image(badge_file)
    elif badge_url:
        final_badge_path = badge_url

    new_challenge = EventChallenge(
        event_id=event.id,
        title=request.form.get('title'),
        description=request.form.get('description'),
        challenge_type=request.form.get('challenge_type'),
        target_value=int(request.form.get('target_value', 1)),
        points=int(request.form.get('points', 10)),
        badge_url=final_badge_path
    )
    db.session.add(new_challenge)
    db.session.commit()
    flash('Challenge added successfully!', 'success')
    return redirect(url_for('manager.manage_events'))

@manager_bp.route('/events/challenge/<int:challenge_id>/edit', methods=['POST'])
def edit_challenge(challenge_id):
    challenge = EventChallenge.query.get_or_404(challenge_id)
    
    challenge.title = request.form.get('title')
    challenge.description = request.form.get('description')
    challenge.challenge_type = request.form.get('challenge_type')
    challenge.target_value = int(request.form.get('target_value', 1))
    challenge.points = int(request.form.get('points', 10))
    
    badge_url = request.form.get('badge_url')
    challenge.badge_url = badge_url if badge_url else None
    
    db.session.commit()
    flash('Challenge updated successfully!', 'success')
    return redirect(url_for('manager.manage_events'))

@manager_bp.route('/events/challenge/<int:challenge_id>/delete', methods=['POST'])
def delete_challenge(challenge_id):
    challenge = EventChallenge.query.get_or_404(challenge_id)
    title = challenge.title
    
    db.session.delete(challenge)
    db.session.commit()
    
    flash(f"Challenge '{title}' successfully removed!", "success")
    return redirect(url_for('manager.manage_events'))

@manager_bp.route('/events/<int:event_id>/delete', methods=['POST'])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    title = event.title
    
    db.session.delete(event)
    db.session.commit()
    
    flash(f"Event '{title}' and all its challenges have been removed.", "success")
    return redirect(url_for('manager.manage_events'))

def sync_event_progress(user_id):
    active_event = Event.query.filter_by(is_active=True).first()
    if not active_event:
        return

    # Real user statistics
    sessions = TestSession.query.filter_by(user_id=user_id).all()
    reports_count = len([s for s in sessions if s.status == 'Concluded'])
    
    issues_count = TestResult.query.join(TestSession).filter(
        TestSession.user_id == user_id,
        TestResult.trigger_status.in_(['FALSE_TRIGGER', 'NO_TRIGGER', 'OK_AFTER_RETEST'])
    ).count()
    
    validated_count = TestResult.query.join(TestSession).filter(
        TestSession.user_id == user_id,
        TestResult.trigger_status.in_(['OK', 'OK_AFTER_RETEST'])
    ).count()

    for challenge in active_event.challenges:
        progress = UserEventProgress.query.filter_by(user_id=user_id, challenge_id=challenge.id).first()
        
        if not progress:
            # CORREÇÃO 1: Forçar explicitamente o current_value para 0 na criação
            progress = UserEventProgress(user_id=user_id, challenge_id=challenge.id, current_value=0)
            db.session.add(progress)

        # Atualiza baseado no tipo
        if challenge.challenge_type == 'auto_reports':
            progress.current_value = reports_count
        elif challenge.challenge_type == 'auto_issues':
            progress.current_value = issues_count
        elif challenge.challenge_type == 'auto_validated':
            progress.current_value = validated_count
        
        # CORREÇÃO 2: Rede de segurança. Se por acaso for None, transforma em 0
        current_val = progress.current_value if progress.current_value is not None else 0
        target_val = challenge.target_value if challenge.target_value is not None else 1
        
        # Verifica se completou usando os valores seguros
        if current_val >= target_val:
            if not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = datetime.utcnow()
    
    db.session.commit()

def save_and_compress_image(upload_file):
    if not upload_file or upload_file.filename == '':
        return None

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'events')
    os.makedirs(upload_folder, exist_ok=True)
    
    filename = f"{uuid.uuid4().hex}.webp"
    filepath = os.path.join(upload_folder, filename)
    
    try:
        img = Image.open(upload_file)
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.thumbnail((256, 256))
        
        img.save(filepath, 'WEBP', quality=80)
        
        return f"/static/uploads/events/{filename}"
    except Exception as e:
        print(f"Error processing image: {e}")
        return None