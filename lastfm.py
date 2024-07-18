import requests

API_KEY = 'd015dbb01ebdf8d0ac71c7cf807da392'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/'

def get_artist_info(artist_name):
    params = {
        'method': 'artist.getinfo',
        'artist': artist_name,
        'api_key': API_KEY,
        'format': 'json',
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

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

def main():
    artist_name = 'Coldplay'

    # Obter a lista de álbuns do artista
    albums_info = get_artist_albums(artist_name)
    if 'topalbums' in albums_info:
        albums = albums_info['topalbums']['album']
        print("\nAlbums and Covers:")
        for album in albums[:5]:  # Limitar aos 5 principais álbuns
            album_name = album['name']
            album_info = get_album_info(artist_name, album_name)
            if 'album' in album_info:
                images = album_info['album']['image']
                image_urls = {image['size']: image['#text'] for image in images}
                print(f"Album: {album_name}")
                for size, url in image_urls.items():
                    print(f"  {size}: {url}")
    else:
        print("No albums found for the artist.")

if __name__ == "__main__":
    main()
