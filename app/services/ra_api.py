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

    authors_data = {} # Usaremos um dicionário para guardar {Nome: {id: X, pic: Y}} 
    
    for ach_id, ach_info in achievements_dict.items():
        author_name = ach_info.get('Author', '').strip()
        if author_name and author_name not in authors_data:
            user_id, user_pic = get_user_stable_data(author_name)
            authors_data[author_name] = {'id': user_id, 'pic': user_pic}
            
    # Escolhemos o primeiro autor como Lead para a imagem principal do card
    if authors_data:
        lead_name = list(authors_data.keys())[0]
        game_data['developer'] = " / ".join(authors_data.keys())
        game_data['developer_id'] = authors_data[lead_name]['id']
        # Guardamos o caminho exato da imagem que a API nos deu!
        game_data['developer_pic'] = authors_data[lead_name]['pic']

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
            'image_icon': data.get('ImageIcon'),
            'console_name': data.get('ConsoleName'),
            'achievements': []
        }
        achievements_dict = data.get('Achievements', {})
        authors = set()
        for ach_id, ach_info in achievements_dict.items():
            author = ach_info.get('Author')
            if author:
                authors.add(author.strip())
                
            game_data['achievements'].append({
                'id': ach_info.get('ID'),
                'title': ach_info.get('Title'),
                'description': ach_info.get('Description'),
                'points': ach_info.get('Points')
            })
        if len(authors) > 1:
            game_data['developer'] = " / ".join(list(authors))
            game_data['is_collab'] = True
        elif len(authors) == 1:
            game_data['developer'] = list(authors)[0]
            game_data['is_collab'] = False
        else:
            game_data['developer'] = "Unknown"
            game_data['is_collab'] = False
            
        return game_data, None
        
    except requests.exceptions.RequestException as e:
        return None, f"Erro de comunicação: {str(e)}"