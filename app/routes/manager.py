from flask import Blueprint

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/')
def index():
    return "Dashboard de Revisão: Consolidado de jogos aguardando CR"

@manager_bp.route('/import')
def import_game():
    return "Local ID para puxar ID game API V2"