import discord
from discord.ext import commands
import requests
import yt_dlp as youtube_dl
import asyncio
from io import BytesIO

API_KEY = 'd015dbb01ebdf8d0ac71c7cf807da392'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/'

# Funções para obter informações dos álbuns
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

# Função para obter informações do usuário
def get_user_info(username):
    params = {
        'method': 'user.getinfo',
        'user': username,
        'api_key': API_KEY,
        'format': 'json',
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

# Função para obter as músicas mais escutadas do usuário
def get_top_tracks(username):
    params = {
        'method': 'user.gettoptracks',
        'user': username,
        'api_key': API_KEY,
        'format': 'json',
        'limit': 5  # Limitar aos 5 principais faixas
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

# Configuração do yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True  # Habilitar o privilégio de conteúdo da mensagem
intents.messages = True  # Habilitar o privilégio de ler mensagens
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("Você precisa estar em um canal de voz para usar este comando.")

@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send("O bot não está em um canal de voz.")

@bot.command(name='play')
async def play(ctx, *, query: str):
    async with ctx.typing():
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print(f'Erro ao reproduzir: {e}') if e else None)
        await ctx.send(f'Tocando: {player.title}')

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
    else:
        await ctx.send("O bot não está tocando nenhuma música no momento.")

@bot.command(name='albuns')
async def fetch_albums(ctx, *, artist_name: str):
    albums_info = get_artist_albums(artist_name)
    if 'topalbums' in albums_info:
        albums = albums_info['topalbums']['album']
        if not albums:
            await ctx.send(f'Nenhum álbum encontrado para o artista {artist_name}.')
            return
        for album in albums[:5]:  # Limitar aos 5 principais álbuns
            album_name = album['name']
            album_info = get_album_info(artist_name, album_name)
            if 'album' in album_info:
                images = album_info['album']['image']
                image_urls = {
                    image['size']: image['#text'] for image in images if image['#text']
                }
                if image_urls:
                    # Baixar a imagem de tamanho médio
                    image_url = image_urls.get('medium')
                    if image_url:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            image_data = BytesIO(response.content)
                            embed = discord.Embed(
                                title=f'Album: {album_name}',
                                description=f'Artist: {artist_name}',
                            )
                            embed.set_image(url="attachment://image.png")
                            await ctx.send(file=discord.File(image_data, 'image.png'), embed=embed)
                        else:
                            await ctx.send(f'Não foi possível baixar a imagem para {album_name}.')
            else:
                await ctx.send(f'Informações do álbum não encontradas para {album_name}.')
    else:
        await ctx.send(f'Nenhum álbum encontrado para o artista {artist_name}.')

@bot.command(name='clear_channel')
@commands.has_permissions(administrator=True)  # Verifica se o usuário tem permissão de administrador
async def clear_channel(ctx, channel_id: int):
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send(f'Canal com ID {channel_id} não encontrado.')
        return
    
    # Confirmação antes de apagar todas as mensagens
    def check(m):
        return m.author == ctx.author and m.content.lower() in ["sim", "não"]

    await ctx.send(f'Tem certeza que deseja apagar todas as mensagens no canal {channel.name}? Responda com "sim" ou "não".')
    try:
        confirmation = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await ctx.send("Tempo esgotado para a confirmação.")
        return

    if confirmation.content.lower() == "sim":
        deleted = await channel.purge(limit=None)  # Apaga todas as mensagens do canal
        await ctx.send(f'{len(deleted)} mensagens apagadas no canal {channel.name}.')
    else:
        await ctx.send("Operação cancelada.")

@bot.command(name='commands')
async def show_commands(ctx):
    commands_list = [command.name for command in bot.commands]
    commands_description = "\n".join([f'!{cmd}' for cmd in commands_list])
    embed = discord.Embed(
        title="Comandos Disponíveis",
        description=commands_description,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='scrobbles')
async def fetch_scrobbles(ctx, username: str):
    user_info = get_user_info(username)
    if 'user' in user_info:
        user = user_info['user']
        scrobbles = user['playcount']
        profile_image_url = user['image'][-1]['#text']  # Última imagem geralmente é a de maior resolução
        embed = discord.Embed(
            title=f'Usuário: {username}',
            description=f'Quantidade de Scrobbles: {scrobbles}',
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=profile_image_url)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'Não foi possível encontrar informações para o usuário {username}.')

@bot.command(name='toptracks')
async def fetch_top_tracks(ctx, username: str):
    top_tracks_info = get_top_tracks(username)
    if 'toptracks' in top_tracks_info:
        tracks = top_tracks_info['toptracks']['track']
        if not tracks:
            await ctx.send(f'Nenhuma faixa encontrada para o usuário {username}.')
            return
        
        description = ""
        for track in tracks:
            track_name = track['name']
            artist_name = track['artist']['name']
            play_count = track['playcount']
            description += f"{track_name} por {artist_name} - {play_count} scrobbles\n"
        
        embed = discord.Embed(
            title=f'Top 5 Faixas de {username}',
            description=description,
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'Não foi possível encontrar informações para o usuário {username}.')

@bot.command(name='albumtracks')
async def fetch_album_tracks(ctx, artist_name: str, *, album_name: str):
    album_info = get_album_info(artist_name, album_name)
    if 'album' in album_info:
        album = album_info['album']
        tracks = album.get('tracks', {}).get('track', [])
        if not tracks:
            await ctx.send(f'Nenhuma faixa encontrada para o álbum {album_name} do artista {artist_name}.')
            return
        
        description = ""
        for track in tracks:
            track_name = track['name']
            duration = track.get('duration')
            if duration is None:
                duration = 0
            else:
                duration = int(duration)
            minutes = duration // 60
            seconds = duration % 60
            description += f"{track_name} - {minutes}:{seconds:02d}\n"
        
        embed = discord.Embed(
            title=f'Faixas do álbum {album_name} de {artist_name}',
            description=description,
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'Não foi possível encontrar informações para o álbum {album_name} do artista {artist_name}.')

# Substitua 'YOUR_DISCORD_BOT_TOKEN' pelo token do seu bot
bot.run('MTA2ODIwNTc2NzA4NzM1Nzk4Mg.GAXrE1.iidOtjQ9S3-oKPxfShDenXlpAuxIWzn7uYMOHA')