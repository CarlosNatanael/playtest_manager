from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash
from app.models import User, db
import json
import os

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

    if 'username' in session and 'role' in session and 'user_id' in session:
        return redirect_by_role(session['role'])
    
    elif 'username' in session:
        session.clear()

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
        stored_password = user_data['password']
        
        is_valid_password = False
        if stored_password.startswith('scrypt:') or stored_password.startswith('pbkdf2:'):
            is_valid_password = check_password_hash(stored_password, password)
        else:
            is_valid_password = (stored_password == password)

        if not is_valid_password:
            flash('Incorrect password.', 'danger')
            return redirect(url_for('auth.login'))
            
        user_db_record = User.query.filter_by(ra_username=username).first()
        
        if not user_db_record:
            user_db_record = User(ra_username=username, role=user_data['role'])
            db.session.add(user_db_record)
            db.session.commit()

        session['username'] = username
        session['role'] = user_data['role']
        session['user_id'] = user_db_record.id

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
    else:
        return redirect(url_for('dashboard.index'))