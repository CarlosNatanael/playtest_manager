import os
import json
import requests
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app

auth_bp = Blueprint('auth', __name__)

def get_allowed_users():
    file_path = os.path.join(current_app.instance_path, 'allowed_users.json')
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session and 'role' in session:
        return redirect_by_role(session['role'])

    if request.method == 'POST':
        username = request.form.get('username')
        api_key = request.form.get('api_key')

        if not username or not api_key:
            flash('Please enter both Username and Web API Key.', 'warning')
            return redirect(url_for('auth.login'))

        allowed_users = get_allowed_users()
        if username not in allowed_users:
            flash('Access Denied: You do not have an authorized role in Playtest Coordinator.', 'danger')
            return redirect(url_for('auth.login'))

        api_url = f"https://retroachievements.org/API/API_GetUserProfile.php?z={username}&y={api_key}&u={username}"
        
        headers = {
            'User-Agent': 'PlaytestManager/1.0'
        }
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            data = response.json()

            if type(data) is not dict or data.get('User') != username:
                flash('Credenciais inválidas na RetroAchievements.', 'danger')
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            flash(f'Erro ao conectar com a RetroAchievements.', 'danger')
            return redirect(url_for('auth.login'))

        session['username'] = username
        session['role'] = allowed_users[username]

        return redirect_by_role(session['role'])

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

def redirect_by_role(role):
    if role == 'Engineer':
        return redirect(url_for('manager.engineer_dashboard'))
    elif role == 'Playtest Manager':
        return redirect(url_for('manager.dashboard'))
    elif role == 'QA':
        return redirect(url_for('qa.dashboard'))
    elif role == 'CR':
        return redirect(url_for('cr.dashboard'))
    else:
        return redirect(url_for('dashboard.index'))