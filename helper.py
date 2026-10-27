import base64
import json
import random
import string
from typing import Optional
import httpx
import endpoints
from pyDes import *
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from functools import lru_cache
from fastapi.concurrency import run_in_threadpool
import asyncio



async def get_color_async(image_url: str):
    return await run_in_threadpool(get_dominant_color_from_image, image_url)


async def attach_colors_bulk(items, image_key="image"):
    unique_images = list({
        item[image_key] for item in items if item.get(image_key)
    })

    colors = await asyncio.gather(
        *[get_color_async(img) for img in unique_images]
    )

    color_map = dict(zip(unique_images, colors))

    for item in items:
        item["color_code"] = color_map.get(item.get(image_key))

def saturation(rgb):
    r, g, b = rgb
    mx = max(rgb)
    mn = min(rgb)
    if mx == 0:
        return 0
    return (mx - mn) / mx

@lru_cache(maxsize=1000)
def get_dominant_color_from_image(image_url: str):
    # 1️⃣ Network (with timeout)
    response = requests.get(image_url, timeout=8)
    image = Image.open(BytesIO(response.content)).convert("RGB")

    # 2️⃣ Resize aggressively (huge CPU win)
    image = image.resize((64, 64))

    pixels = np.array(image).reshape(-1, 3)

    # 3️⃣ Remove near-white & near-black pixels
    filtered = [
        tuple(p) for p in pixels
        if not (max(p) > 245 and min(p) > 245)
        and not (max(p) < 15)
    ]

    if not filtered:
        filtered = pixels

    # 4️⃣ Pick most vibrant color
    vibrant = max(filtered, key=saturation)

    return rgb_to_hex(tuple(map(int, vibrant)))
    
    
    

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


async def format_song(data, lyrics):
    try:
        data['media_url'] = decrypt_url(data['encrypted_media_url'])
        if data['320kbps'] != "true":
            data['media_url'] = data['media_url'].replace(
                "_320.mp4", "_160.mp4")
        data['media_preview_url'] = data['media_url'].replace(
            "_320.mp4", "_96_p.mp4").replace("_160.mp4", "_96_p.mp4").replace("//aac.", "//preview.")
    except KeyError or TypeError:
        url = data['media_preview_url']
        url = url.replace("preview", "aac")
        if data['320kbps'] == "true":
            url = url.replace("_96_p.mp4", "_320.mp4")
        else:
            url = url.replace("_96_p.mp4", "_160.mp4")
        data['media_url'] = url
    
    data['song'] = format(data['song'])
    data['music'] = format(data['music'])
    data['singers'] = format(data['singers'])
    data['starring'] = format(data['starring'])
    data['album'] = format(data['album'])
    data["primary_artists"] = format(data["primary_artists"])
    data['image'] = data['image'].replace("150x150", "500x500")
    data['color_code']= await get_color_async(data['image'])
    if lyrics:
        if data['has_lyrics'] == 'true':
            data['lyrics'] = await get_lyrics(data['id'])
        else:
            data['lyrics'] = None

    try:
        data['copyright_text'] = data['copyright_text'].replace("&copy;", "©")
    except KeyError:
        pass
    return data


async def format_album(data, lyrics):
    data['image'] = data['image'].replace("150x150", "500x500")
    data['name'] = format(data['name'])
    data['primary_artists'] = format(data['primary_artists'])
    data['title'] = format(data['title'])
    for song in data['songs']:
        song = await format_song(song, lyrics)
    return data


async def format_playlist(data, lyrics):
    data['firstname'] = format(data['firstname'])
    data['listname'] = format(data['listname'])
    for song in data['songs']:
        song = await format_song(song, lyrics)
    return data


def format(string):
    return string.encode().decode().replace("&quot;", "").replace("&amp;", "").replace("&#039;", "")


def decrypt_url(url):
    des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0",
                     pad=None, padmode=PAD_PKCS5)
    enc_url = base64.b64decode(url.strip())
    dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
    dec_url = dec_url.replace("_96.mp4", "_320.mp4")
    return dec_url

async def get_lyrics(id):
    lyrics_url = endpoints.lyrics_base_url+id
    async with httpx.AsyncClient() as cl:
        res = await cl.get(lyrics_url)
        res = res.json()
        return res['lyrics']
    


def format_search(data: map):
    """Format a JioSaavn song JSON response into a simplified dict."""

    try:
        # Handle missing keys gracefully
        more_info = data["more_info"]

        # --- Media URL logic ---
        encrypted_url = more_info["encrypted_media_url"]
        media_url = ""
        try:
            media_url = decrypt_url(encrypted_url)
            if more_info.get("320kbps") != "true":
                media_url = media_url.replace("_320.mp4", "_160.mp4")
            # create preview link
            media_preview_url = media_url.replace(
                "_320.mp4", "_96_p.mp4"
            ).replace("_160.mp4", "_96_p.mp4").replace("//aac.", "//preview.")
        except Exception:
            # fallback if decrypt_url fails
            preview_url = more_info.get("media_preview_url", "")
            media_url = preview_url.replace("preview", "aac")
            if more_info.get("320kbps") == "true":
                media_url = media_url.replace("_96_p.mp4", "_320.mp4")
            else:
                media_url = media_url.replace("_96_p.mp4", "_160.mp4")

        # --- Image ---
        img = data.get("image","")
        
        image_url = data.get("image", "").replace("150x150", "500x500")
        
        # --- Artists ---
        artist_map = more_info.get("artistMap", {})
        primary_artists = artist_map.get("primary_artists", [])
        artist_names = [a["name"] for a in primary_artists] if primary_artists else []

        starring_list = [
            a["name"] for a in artist_map.get("artists", []) if a.get("role") == "starring"
        ]

        # --- Output formatted response ---
        formatted = {
            "songname": format(data.get("title", "")),
            "type": data.get("type", ""),
            "artist": ", ".join(artist_names),
            "media_url": media_url,
            "image_url": image_url,
            "starring": ", ".join(starring_list),
            "album_name": format(more_info.get("album", "")),
            "album_id": more_info.get("album_id", ""),
            "album_url": more_info.get("album_url", ""),
            "color_code":None
        }

        return formatted


    except Exception as e:
        print("Error formatting song:", e)
        return {}

def formatPlaylistSearchResults(res):
    formated = []
    for li in res['results']:
             data = {
                 "id":li['id'],
                 "title":format(li['title']),
                 "type":li['type'],
                 "language":li['more_info']['language'],
                 "artist":format(li['more_info']['firstname']+li['more_info']['lastname']),
                 "image_url":li['image'],
             }
             formated.append(data)
    return formated

def formatAlbumSearchResults(res):
        formated = []
        for li in res['results']:
             data = {
                 "id":li['id'],
                 "title":format(li['title']),
                 "type":li['type'],
                 "language":li['language'],
                 "artist":format(li['more_info']['music']),
                 "image_url":li['image'],
             }
             formated.append(data)
        return formated   
def formatSongSearchResults(res):
        formated = []
        for li in res['results']:
             data = {
                 "id":li['more_info']['album_id'],
                 "title":format(li['title']),
                 "type":li['type'],
                 "language":li['language'],
                 "artist":format(li['more_info']['music']),
                 "image_url":li['image'],
                 
             }
             formated.append(data)
        return formated   


def generate_room_code(length=6):
    return ''.join(
        random.choices(
            string.ascii_uppercase+string.digits,
            k=length
        )
    )

async def get_song(id, lyrics):
    try:
        song_details_base_url = endpoints.song_details_base_url+id
        song_response = requests.get(
            song_details_base_url).text.encode().decode('unicode-escape')
        song_response = json.loads(song_response)
        song_data = await format_song(song_response[id], lyrics)
        if song_data:
            return song_data
    except:
        return None
