import requests
import os
from flask import current_app

RA_API_BASE_URL = "https://retroachievements.org/api/v2"

def _get_headers(access_token=None):
    """Monta o cabeçalho de autenticação dependendo do cenário."""
    if access_token:
        return {"Authorization": f"Bearer {access_token}"}
    
    api_key = current_app.config.get('RA_API_KEY')
    if api_key:
        return {"X-API-Key": api_key}
    return {}

def fetch_game_and_achievements(game_id, access_token=None):
    """
    Bate na API V2, puxa os dados do jogo e as conquistas Unofficial.
    Retorna um dicionário padronizado para o nosso Manager salvar no banco.
    """
    url = f"{RA_API_BASE_URL}/games/{game_id}"
    headers = _get_headers(access_token)
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        game_data = {
            'id': data.get('ID'),
            'title': data.get('Title'),
            'developer': data.get('Developer'),
            'achievements': []
        }
        return game_data, None
    except requests.exceptions.RequestException as e:
        return None, f"Erro ao comunicar com a API do RA: {str(e)}"