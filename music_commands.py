import asyncio
from collections import Counter
from datetime import datetime, timedelta
from io import BytesIO
import os
import discord
import matplotlib.pyplot as plt
import requests
from discord.ext import commands
from PIL import Image
import imgkit

from api.lastfm import (get_album_info, get_artist_albums, get_recent_tracks,
                        get_track_tags, get_user_info, get_user_top_tracks, get_user_top_albums)
from api.yt_dlp_config import YTDLSource

# Configuração dos intents
intents = discord.Intents.default()
intents.message_content = True  # Habilitar privilégio de leitura de mensagens

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
        await ctx.send(
            'Você precisa estar em um canal de voz para usar este comando.'
        )


@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send('O bot não está em um canal de voz.')


@bot.command(name='play')
async def play(ctx, *, query: str):
    async with ctx.typing():
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        ctx.voice_client.play(
            player,
            after=lambda e: print(f'Erro ao reproduzir: {e}') if e else None,
        )
        await ctx.send(f'Tocando: {player.title}')


@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
    else:
        await ctx.send('O bot não está tocando nenhuma música no momento.')


@bot.command(name='albuns')
async def fetch_albums(ctx, *, artist_name: str):
    albums_info = get_artist_albums(artist_name)
    if 'topalbums' in albums_info:
        albums = albums_info['topalbums']['album']
        if not albums:
            await ctx.send(
                f'Nenhum álbum encontrado para o artista {artist_name}.'
            )
            return
        for album in albums[:5]:
            album_name = album['name']
            album_info = get_album_info(artist_name, album_name)
            if 'album' in album_info:
                images = album_info['album']['image']
                image_urls = {
                    img['size']: img['#text'] for img in images if img['#text']
                }
                if image_urls:
                    image_url = image_urls.get('medium')
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        image_data = BytesIO(response.content)
                        embed = discord.Embed(
                            title=f'Álbum: {album_name}',
                            description=f'Artista: {artist_name}',
                        )
                        embed.set_image(url='attachment://image.png')
                        await ctx.send(
                            file=discord.File(image_data, 'image.png'),
                            embed=embed,
                        )
                    else:
                        await ctx.send(
                            f'Não foi possível baixar a imagem para {album_name}.'
                        )
            else:
                await ctx.send(
                    f'Informações do álbum não encontradas para {album_name}.'
                )
    else:
        await ctx.send(
            f'Nenhum álbum encontrado para o artista {artist_name}.'
        )


@bot.command(name='clear_channel')
@commands.has_permissions(administrator=True)
async def clear_channel(ctx, channel_id: int):
    """Comando para limpar todas as mensagens de um canal rapidamente."""
    channel = bot.get_channel(channel_id)

    if channel is None:
        await ctx.send(f'Canal com ID {channel_id} não encontrado.')
        return

    await ctx.send(f'Iniciando a limpeza do canal {channel.name}...')

    try:
        # Excluir mensagens em blocos para evitar limites da API
        deleted = await channel.purge(limit=None, bulk=True)
        await ctx.send(
            f'{len(deleted)} mensagens apagadas do canal {channel.name}.',
            delete_after=5,
        )
    except Exception as e:
        await ctx.send(f'Ocorreu um erro ao apagar as mensagens: {e}')


@bot.command(name='commands')
async def show_commands(ctx):
    commands_list = [command.name for command in bot.commands]
    commands_description = '\n'.join([f'!{cmd}' for cmd in commands_list])
    embed = discord.Embed(
        title='Comandos Disponíveis',
        description=commands_description,
        color=discord.Color.blue(),
    )
    await ctx.send(embed=embed)


@bot.command(name='scrobbles')
async def fetch_scrobbles(ctx, username: str):
    user_info = get_user_info(username)
    if 'user' in user_info:
        user = user_info['user']
        scrobbles = user['playcount']
        profile_image_url = user['image'][-1]['#text']
        embed = discord.Embed(
            title=f'Usuário: {username}',
            description=f'Scrobbles: {scrobbles}',
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=profile_image_url)
        await ctx.send(embed=embed)
    else:
        await ctx.send(
            f'Não foi possível encontrar informações para o usuário {username}.'
        )


@bot.command(name='toptracks')
async def fetch_top_tracks(ctx, username: str):
    top_tracks_info = get_user_top_tracks(username)
    if 'toptracks' in top_tracks_info:
        tracks = top_tracks_info['toptracks']['track']
        if not tracks:
            await ctx.send(
                f'Nenhuma faixa encontrada para o usuário {username}.'
            )
            return
        description = '\n'.join(
            [
                f"{t['name']} por {t['artist']['name']} - {t['playcount']} scrobbles"
                for t in tracks
            ]
        )
        embed = discord.Embed(
            title=f'Top Faixas de {username}',
            description=description,
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(
            f'Não foi possível encontrar informações para o usuário {username}.'
        )


def generate_pie_chart(top_5_tags):
    # Separar labels e valores das tags
    labels = [tag for tag, _ in top_5_tags]
    sizes = [count for _, count in top_5_tags]

    # Criar gráfico de pizza
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    ax.axis('equal')  # Assegura que o gráfico será um círculo

    # Salvar gráfico em um buffer de memória
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close(fig)

    return buffer


@bot.command(name='toptags')
async def fetch_top_tags(ctx, username: str):
    top_tracks_info = get_user_top_tracks(username)

    if 'toptracks' not in top_tracks_info:
        await ctx.send(f'Usuário {username} não encontrado.')
        return

    tracks = top_tracks_info['toptracks']['track']
    tag_counter = Counter()

    for track in tracks:
        artist_name = track['artist']['name']
        track_name = track['name']
        tags_info = get_track_tags(artist_name, track_name)

        if 'toptags' in tags_info and 'tag' in tags_info['toptags']:
            for tag in tags_info['toptags']['tag']:
                tag_counter[tag['name']] += 1

    top_5_tags = tag_counter.most_common(5)

    if not top_5_tags:
        await ctx.send(f'Nenhuma tag encontrada para o usuário {username}.')
        return

    # Gerar gráfico de pizza e enviar como imagem
    chart_buffer = generate_pie_chart(top_5_tags)
    await ctx.send(file=discord.File(chart_buffer, 'toptags.png'))


@bot.command(name='albumtracks')
async def fetch_album_tracks(ctx, artist_name: str, *, album_name: str):
    album_info = get_album_info(artist_name, album_name)
    if 'album' in album_info:
        album = album_info['album']
        tracks = album.get('tracks', {}).get('track', [])
        if not tracks:
            await ctx.send(
                f'Nenhuma faixa encontrada para o álbum "{album_name}" de {artist_name}.'
            )
            return
        description = '\n'.join(
            [
                f"{t['name']} - {int(t['duration']) // 60}:{int(t['duration']) % 60:02d}"
                for t in tracks
            ]
        )
        embed = discord.Embed(
            title=f'Faixas do álbum "{album_name}"',
            description=description,
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'Informações do álbum "{album_name}" não encontradas.')


@bot.command(name='comum')
async def fetch_common_tracks(ctx, user1: str, user2: str, days: int):
    # Definir o período de tempo (últimos X dias)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    # Obter faixas recentes para ambos os usuários
    tracks_user1 = get_recent_tracks(user1, start_time, end_time)
    tracks_user2 = get_recent_tracks(user2, start_time, end_time)

    if not tracks_user1 or not tracks_user2:
        await ctx.send(
            f'Não foi possível encontrar faixas para um ou ambos os usuários.'
        )
        return

    # Extrair nome das faixas e artistas de ambos os usuários
    set_user1 = {
        (track['name'], track['artist']['#text']) for track in tracks_user1
    }
    set_user2 = {
        (track['name'], track['artist']['#text']) for track in tracks_user2
    }

    # Encontrar faixas em comum
    common_tracks = set_user1.intersection(set_user2)

    if not common_tracks:
        await ctx.send(
            f'Nenhuma faixa em comum encontrada entre {user1} e {user2} nos últimos {days} dias.'
        )
        return

    # Construir a mensagem com as faixas em comum
    description = '\n'.join(
        [f'{track[0]} por {track[1]}' for track in common_tracks]
    )

    embed = discord.Embed(
        title=f'Músicas em Comum entre {user1} e {user2}',
        description=description,
        color=discord.Color.green(),
    )

    await ctx.send(embed=embed)


@bot.command(name='mosaico')
async def fetch_album_mosaic(ctx, username: str):
    """Gera um mosaico com as capas dos 10 álbuns mais ouvidos de um usuário usando HTML e CSS."""
    
    api_key = "YOUR_API_KEY"
    
    # Obtém os álbuns mais ouvidos
    top_albums_info = get_user_top_albums(username, api_key)
    
    if not top_albums_info or 'topalbums' not in top_albums_info:
        await ctx.send(f"Não foi possível encontrar álbuns para o usuário {username}.")
        return

    # Coletar URLs das imagens dos álbuns
    album_images = []
    for album in top_albums_info['topalbums']['album'][:10]:
        images = album.get('image', [])
        image_url = next((img['#text'] for img in images if img['size'] == 'large'), None)
        if image_url:
            album_images.append(image_url)

    if not album_images:
        await ctx.send(f"Não foi possível recuperar as imagens dos álbuns para o usuário {username}.")
        return

    # Criar HTML com CSS para o mosaico
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #1e1e1e;
                color: #fff;
                font-family: Arial, sans-serif;
            }}
            .mosaic {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                grid-gap: 10px;
                width: 90%;
                max-width: 800px;
            }}
            .mosaic img {{
                width: 100%;
                height: auto;
                border-radius: 5px;
            }}
            h1 {{
                text-align: center;
                font-size: 24px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div>
            <h1>Mosaico dos 10 álbuns mais ouvidos de {username}</h1>
            <div class="mosaic">
                {''.join(f'<img src="{url}" alt="Album cover">' for url in album_images)}
            </div>
        </div>
    </body>
    </html>
    """

    # Salvar o HTML em um arquivo temporário
    with open("mosaic.html", "w") as f:
        f.write(html_content)

    # Converter HTML para imagem usando imgkit e salvar em um arquivo temporário
    imgkit_options = {
        'format': 'png',
        'quality': '100'
    }
    output_path = "mosaic.png"
    imgkit.from_file("mosaic.html", output_path, options=imgkit_options)

    # Enviar a imagem no Discord
    await ctx.send(file=discord.File(output_path))

    # Remover os arquivos temporários
    os.remove("mosaic.html")
    os.remove(output_path)

