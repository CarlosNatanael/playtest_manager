from flask import Blueprint, render_template, request, redirect, url_for
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
            return "Error: Game ID is required", 400
        
        existing_game = Game.query.get(game_id)
        if existing_game:
            return f"<h3>Warning</h3><p>The game '{existing_game.title}' is already in the database!</p><a href='/dashboard'>Back to Dashboard</a>"
        
        game_data, error = fetch_game_and_achievements(game_id)

        if error or not game_data:
            return f"<h3>API Error</h3><p>{error or 'Game not found.'}</p>", 500
        
        dev_level = 'Junior'

        new_game = Game(
            id=game_data['id'],
            title=game_data['title'],
            developer=game_data['developer'] or 'Unknown',
            developer_level=dev_level,
            status='Open'
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
        
        return f"<h3>Success!</h3><p>{new_game.title} imported with {len(game_data.get('achievements', []))} achievements.</p><a href='/dashboard'>View in Dashboard</a>"

    return render_template('manager/import.html')