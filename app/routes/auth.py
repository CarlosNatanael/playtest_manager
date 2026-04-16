import os
import json
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app
from app.models import User, db

auth_bp = Blueprint('auth', __name__)

def get_allowed_users():
    file_path = os.path.join(current_app.instance_path, 'allowed_users.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {} 

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session and 'role' in session:
        return redirect_by_role(session['role'])

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password') 

        if not username or not password:
            flash('Please enter your Username and Password.', 'warning')
            return redirect(url_for('auth.login'))

        users_db = get_allowed_users()
        if username not in users_db:
            flash('Access Denied: Your user is not registered in the team.', 'danger')
            return redirect(url_for('auth.login'))
        
        user_data = users_db[username]
        if user_data['password'] != password:
            flash('Incorrect password.', 'danger')
            return redirect(url_for('auth.login'))
            
        user_db = User.query.filter_by(ra_username=username).first()
        
        if not user_db:
            user_db = User(ra_username=username, role=user_data['role'])
            db.session.add(user_db)
            db.session.commit()
        session['username'] = username
        session['role'] = user_data['role']
        session['user_id'] = user_db.id

        return redirect_by_role(session['role'])

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have successfully logged out.', 'info')
    return redirect(url_for('auth.login'))

def redirect_by_role(role):
    if role == 'Engineer':
        return redirect(url_for('manager.engineer_dashboard'))
    elif role == 'Playtest Manager':
        return redirect(url_for('manager.index'))
    elif role == 'QA':
        return redirect(url_for('qa.dashboard'))
    elif role == 'CR':
        return redirect(url_for('cr.dashboard'))
    else:
        return redirect(url_for('dashboard.index'))