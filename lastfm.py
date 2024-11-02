import os

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')
BASE_URL = 'http://ws.audioscrobbler.com/2.0/'


def get_artist_albums(artist_name):
    params = {
        'method': 'artist.gettopalbums',
        'artist': artist_name,
        'api_key': API_KEY,
        'format': 'json',
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()


def get_album_info(artist_name, album_name):
    params = {
        'method': 'album.getinfo',
        'artist': artist_name,
        'album': album_name,
        'api_key': API_KEY,
        'format': 'json',
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()


def get_user_info(username):
    params = {
        'method': 'user.getinfo',
        'user': username,
        'api_key': API_KEY,
        'format': 'json',
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()


def get_user_top_tracks(username):
    params = {
        'method': 'user.gettoptracks',
        'user': username,
        'api_key': API_KEY,
        'format': 'json',
        'limit': 50,
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()


def get_track_tags(artist, track):
    params = {
        'method': 'track.gettoptags',
        'artist': artist,
        'track': track,
        'api_key': API_KEY,
        'format': 'json',
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()


def get_recent_tracks(username, start_time, end_time):
    """Função para buscar faixas recentes de um usuário em um período de tempo."""
    params = {
        'method': 'user.getrecenttracks',
        'user': username,
        'api_key': API_KEY,
        'format': 'json',
        'from': int(start_time.timestamp()),
        'to': int(end_time.timestamp()),
        'limit': 200,  # Limitar a 200 faixas
    }
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if 'recenttracks' in data and 'track' in data['recenttracks']:
        return data['recenttracks']['track']
    return []


import requests

def get_user_top_albums(username, limit=10, period='overall'):
    """Obtém os álbuns mais ouvidos de um usuário do Last.fm."""
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        'method': 'user.gettopalbums',
        'user': username,
        'api_key': API_KEY,
        'format': 'json',
        'limit': limit,
        'period': period
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'topalbums' in data:
            return data
        else:
            print("Erro: Dados de álbuns não encontrados na resposta.")
            return None
    else:
        print(f"Erro ao acessar a API: {response.status_code}")
        return None

