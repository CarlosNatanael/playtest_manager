from flask import Blueprint, redirect, url_for, session

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role') == 'manager':
        return redirect(url_for('manager.index'))
    else:
        return redirect(url_for('dashboard.index'))