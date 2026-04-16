from flask import Blueprint, redirect, url_for, session, render_template
from app.models import Game

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role') == 'manager':
        return redirect(url_for('manager.index'))
    else:
        return redirect(url_for('dashboard.index'))
    
@public_bp.route('/cr-board')
def cr_board():
    games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template('public/cr.html', games=games)