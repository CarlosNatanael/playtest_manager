from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app
from app.models import User, db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect_by_role(session.get('role'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please enter your username and password.', 'warning')
            return redirect(url_for('auth.login'))
        user = User.query.filter_by(ra_username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("This account has been deactivated by the Administrator.", "danger")
                return redirect(url_for('auth.login'))
            
            session['user_id'] = user.id
            session['username'] = user.ra_username
            session['role'] = user.role
            
            flash(f"Welcome back, {user.ra_username}!", "success")
            return redirect_by_role(user.role)
        else:
            flash("Invalid username or password.", "danger")
            
    return render_template('auth/login.html')

@auth_bp.route('/invite/<token>', methods=['GET', 'POST'])
def setup_password(token):
    user = User.query.filter_by(invite_token=token).first()
    
    if not user or not user.token_expiry or user.token_expiry < datetime.utcnow():
        flash('This invite link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return redirect(url_for('auth.setup_password', token=token))

        user.set_password(new_password)
        user.invite_token = None
        user.token_expiry = None
        db.session.commit()
        
        flash('Password set successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/setup_password.html', token=token, user=user)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

def redirect_by_role(role):
    if role == 'Playtest Manager':
        return redirect(url_for('manager.index'))
    return redirect(url_for('dashboard.index'))