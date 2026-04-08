import requests
from flask import current_app

def get_user_stable_data(username):
    url = "https://retroachievements.org/API/API_GetUserProfile.php"
    params = {
        "z": current_app.config.get('RA_USERNAME'),
        "y": current_app.config.get('RA_API_KEY'),
        "u": username
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        return data.get('ID'), data.get('UserPic')
    except:
        return None, None

def fetch_game_and_achievements(game_id, access_token=None):
    url = "https://retroachievements.org/API/API_GetGameExtended.php"
    username = current_app.config.get('RA_USERNAME')
    api_key = current_app.config.get('RA_API_KEY')
    
    if not username or not api_key:
        return None, "Erro: RA_USERNAME ou RA_API_KEY não configurados."

    params = {"z": username, "y": api_key, "i": game_id, "f": 5}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'ID' not in data:
            return None, "Jogo não encontrado."
        game_data = {
            'id': data.get('ID'),
            'title': data.get('Title'),
            'image_icon': data.get('ImageIcon'),
            'console_name': data.get('ConsoleName'),
            'achievements': []
        }

        achievements_dict = data.get('Achievements', {})
        authors_data = {}
        
        for ach_id, ach_info in achievements_dict.items():
            author_name = ach_info.get('Author', '').strip()
            
            if author_name and author_name not in authors_data:
                u_id, u_pic = get_user_stable_data(author_name)
                authors_data[author_name] = {'id': u_id, 'pic': u_pic}
                
            game_data['achievements'].append({
                'id': ach_info.get('ID'),
                'title': ach_info.get('Title'),
                'description': ach_info.get('Description'),
                'points': ach_info.get('Points'),
                'badge_name': ach_info.get('BadgeName')
            })
        if authors_data:
            names = list(authors_data.keys())
            lead = names[0]
            game_data['developer'] = " / ".join(names)
            game_data['is_collab'] = len(names) > 1
            game_data['developer_id'] = authors_data[lead]['id']
            game_data['developer_pic'] = authors_data[lead]['pic']
        else:
            game_data['developer'] = "Unknown"
            game_data['is_collab'] = False

        return game_data, None
        
    except requests.exceptions.RequestException as e:
        return None, f"Erro de comunicação: {str(e)}"
    
def validate_game_hash(game_id, hash_to_check):
    url = "https://retroachievements.org/API/API_GetGameHashes.php"
    params = {
        "z": current_app.config.get('RA_USERNAME'),
        "y": current_app.config.get('RA_API_KEY'),
        "i": game_id
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        
        results = data.get('Results', [])
        valid_hashes = []
        
        for item in results:
            if isinstance(item, dict) and 'MD5' in item:
                valid_hashes.append(item['MD5'].lower())
            elif isinstance(item, str):
                valid_hashes.append(item.lower())

        return hash_to_check.lower().strip() in valid_hashes
    except:
        return False