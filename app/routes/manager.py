# Adicione o 'flash' aqui nos imports do flask
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Game, Achievement
from app.services.ra_api import fetch_game_and_achievements

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/')
def index():
    games = Game.query.all()
    return render_template('manager/index.html', games=games)

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
        
        dev_level = 'Junior'

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
                points=ach_data['points']
            )
            db.session.add(new_ach)
        db.session.commit()
        
        flash(f"Success! {new_game.title} imported with {len(game_data.get('achievements', []))} achievements.", "success")
        return redirect(url_for('manager.index'))

    return render_template('manager/import.html')