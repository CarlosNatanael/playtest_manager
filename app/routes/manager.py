from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Game, Achievement, TestSession, TestResult, User, GameLog
from app.services.ra_api import get_developer_level, fetch_game_and_achievements
from werkzeug.security import generate_password_hash
from flask import current_app
from datetime import datetime
from app import db
import json
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
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not password or not role:
            flash('All fields are required!', 'warning')
            return redirect(url_for('manager.manage_team'))

        if username in users_db:
            flash(f'User {username} already exists.', 'danger')
            return redirect(url_for('manager.manage_team'))

        hashed_password = generate_password_hash(password)

        users_db[username] = {
            'password': hashed_password,
            'role': role
        }
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(users_db, f, indent=4)

        flash(f'User {username} successfully added to the team!', 'success')
        return redirect(url_for('manager.manage_team'))

    return render_template('manager/team.html', users=users_db)

@manager_bp.route('/team/delete/<username>', methods=['POST'])
def delete_user(username):
    file_path = get_allowed_users_path()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
            
        if username in users_db:
            if username == session.get('username'):
                flash('You cannot delete your own Manager account!', 'danger')
            elif username.lower() == 'bot':
                flash('The System Bot is protected and cannot be removed.', 'warning')
            else:
                del users_db[username]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(users_db, f, indent=4)
                flash(f'Access for {username} has been revoked.', 'info')
                
    except Exception as e:
        flash(f'Error removing user: {e}', 'danger')

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

    concluded_sessions = TestSession.query.filter_by(status='Concluded').all()
    sessions_map = {s.game_id: s for s in concluded_sessions}

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