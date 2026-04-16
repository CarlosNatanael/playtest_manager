from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import Game, Achievement, TestSession, TestResult, User, GameLog
from app.services.ra_api import fetch_game_and_achievements
from datetime import datetime
import json

manager_bp = Blueprint('manager', __name__)

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
            flash("Error: Game ID is required.", "danger")
            return redirect(url_for('manager.import_game'))
        
        existing_game = Game.query.get(game_id)
        if existing_game:
            flash(f"Warning: The game '{existing_game.title}' is already in the database!", "warning")
            return redirect(url_for('manager.index'))
        
        game_data, error = fetch_game_and_achievements(game_id)

        if error or not game_data:
            flash(f"API Error: {error or 'Game not found.'}", "danger")
            return redirect(url_for('manager.import_game'))
        
        dev_level = request.form.get('dev_level', 'Junior')

        new_game = Game(
            id=game_data['id'],
            title=game_data['title'],
            developer=game_data['developer'] or 'Unknown',
            developer_level=dev_level,
            status='Open',
            is_collab=game_data.get('is_collab', False),
            developer_id=game_data.get('developer_id'),
            developer_pic=game_data.get('developer_pic'),
            image_icon=game_data.get('image_icon'), 
            console_name=game_data.get('console_name')
        )
        db.session.add(new_game)

        for ach_data in game_data.get('achievements', []):
            new_ach = Achievement(
                id=ach_data['id'],
                game_id=new_game.id,
                title=ach_data['title'],
                description=ach_data['description'],
                points=ach_data['points'],
                badge_name=ach_data.get('badge_name')
            )
            db.session.add(new_ach)
        db.session.commit()
        
        flash(f"Success! {new_game.title} imported with {len(game_data.get('achievements', []))} achievements.", "success")
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