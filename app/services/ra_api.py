import requests
from flask import current_app

def fetch_game_and_achievements(game_id, access_token=None):
    url = "https://retroachievements.org/API/API_GetGameExtended.php"
    
    username = current_app.config.get('RA_USERNAME')
    api_key = current_app.config.get('RA_API_KEY')
    
    if not username or not api_key:
        return None, "Erro: RA_USERNAME ou RA_API_KEY não configurados no config.py"
    params = {
        "z": username,
        "y": api_key,
        "i": game_id,
        "f": 5
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'ID' not in data:
            return None, "Jogo não encontrado no RetroAchievements."
        game_data = {
            'id': data.get('ID'),
            'title': data.get('Title'),
            'developer': data.get('Developer'),
            'achievements': []
        }
        achievements_dict = data.get('Achievements', {})
        for ach_id, ach_info in achievements_dict.items():
            game_data['achievements'].append({
                'id': ach_info.get('ID'),
                'title': ach_info.get('Title'),
                'description': ach_info.get('Description'),
                'points': ach_info.get('Points')
            })
        return game_data, None
        
    except requests.exceptions.RequestException as e:
        return None, f"Erro de comunicação: {str(e)}"