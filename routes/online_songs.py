import asyncio
import json
import logging
import re
from typing import List
from fastapi import APIRouter,Depends,HTTPException, Request
from sqlalchemy.orm import Session
import httpx
import endpoints

from helper import *
import helper
from database import get_db
from models.app_version import AppVersion
from middleware.auth_middleware import token_auth
from pydantic_shemas.recommandation_schemas import HistoryTrack
from services.gemini_service import GeminiService

logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=['Online Songs API'])
gemini = GeminiService()

timeout=httpx.Timeout(30.0)
@router.post("/search/songs/",status_code=201)
async def search_by_query(query:str,auth:Session=Depends(token_auth)):
        base_url =endpoints.search_all_url
        search_url = base_url+query
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(search_url)
            results = response.json()
            try:
                data = [format_search(res) for res in results['results']]
                
                await attach_colors_bulk(data, image_key="image_url")
		
		
                return data
            except:
                raise HTTPException(400,"Something went Wrong")

@router.post("/search/autocomplete/",status_code=201)
async def auto_complete_search(query: str):
    if len(query)==0:
        query="a"     
    search_url = endpoints.search_base_url+query
    async with httpx.AsyncClient(timeout=timeout) as cl:
        res = await cl.get(search_url)
        res = res.json()
        data ={
            "albums":res['albums']['data'],
            "playlists":res['playlists']['data']
        }
        return data
        
@router.get("/getplaylist/",status_code=200)
async def get_playlist_by_id(id:str,auth:Session=Depends(token_auth)):
    playlist_url = endpoints.playlist_details_base_url+id
    async with httpx.AsyncClient(timeout=timeout) as cl :
        res = await cl.get(playlist_url)
        res = res.json()
        playlist = await format_playlist(res,True)
        return playlist    
        
    
@router.get("/client-version")
def get_client_version(db: Session = Depends(get_db)):
    """
    Returns the latest active client version from PostgreSQL.
    Falls back gracefully to default {versionCode: 12, versionName: 'V2.4.1'} if empty.
    """
    try:
        active = (
            db.query(AppVersion)
            .filter(AppVersion.is_active == True)
            .order_by(AppVersion.version_code.desc(), AppVersion.id.desc())
            .first()
        )
        if active:
            return {
                "versionCode": active.version_code,
                "versionName": active.version_name,
                "download_url": active.download_url,
                "downloadUrl": active.download_url,
                "release_notes": active.release_notes,
                "releaseNotes": active.release_notes,
                "is_force_update": active.is_force_update,
                "isForceUpdate": active.is_force_update,
                "file_size": active.file_size,
                "updated_at": active.updated_at.isoformat() if active.updated_at else None,
            }
    except Exception as e:
        logger.error(f"Error querying dynamic client-version: {e}")

    # Baseline fallback for zero-downtime safety
    return {
        "versionCode": 12,
        "versionName": "V2.4.1",
        "download_url": None,
        "downloadUrl": None,
        "release_notes": "Baseline release",
        "releaseNotes": "Baseline release",
        "is_force_update": False,
        "isForceUpdate": False,
        "file_size": None,
        "updated_at": None,
    }

@router.get("/album/",status_code=200)
async def get_album_data(album_id:str,auth:Session=Depends(token_auth)):
    base_url = endpoints.album_details_base_url
    search_url = base_url+album_id
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.get(search_url)
        res=res.json()
        formated_res =await format_album(res,True)
        try:
        
            data={
                "title":formated_res['title'],
                "name":formated_res['name'],
                "year":formated_res['year'],
                "artist":formated_res['primary_artists'],
                "album_id":formated_res['albumid'],
                "image_url":formated_res['image'],
                "songs":formated_res['songs']  
            }
            return data
        except Exception as e:
            raise HTTPException(400,e.args)

        

async def get_albums_search_results(query:str):
    album_search_url = f"https://www.jiosaavn.com/api.php?p=1&q={query}&_format=json&_marker=0&api_version=4&ctx=web6dot0&n=20&__call=search.getAlbumResults"
    async with httpx.AsyncClient(timeout=timeout) as client:
         res = await client.get(album_search_url)
         res=res.json()
    return formatAlbumSearchResults(res)  



async def get_playlists_search_results(query:str):
    album_search_url = f"https://www.jiosaavn.com/api.php?p=1&q={query}&_format=json&_marker=0&api_version=4&ctx=web6dot0&n=20&__call=search.getPlaylistResults"
    async with httpx.AsyncClient(timeout=timeout) as client:
         res = await client.get(album_search_url)
         res=res.json()
         
    return formatPlaylistSearchResults(res)  


async def get_songs_search_results(query:str):
    album_search_url = f"https://www.jiosaavn.com/api.php?p=1&q={query}&_format=json&_marker=0&api_version=4&ctx=web6dot0&n=20&__call=search.getResults"
    async with httpx.AsyncClient(timeout=timeout) as client:
         res = await client.get(album_search_url)
         res=res.json()
    return formatSongSearchResults(res)  

@router.post("/searchv2",status_code=201)
async def get_searchv2_results(query:str):
    songs = await get_songs_search_results(query)
    playlists = await get_playlists_search_results(query)
    albums = await get_albums_search_results(query)
    data ={
        "songs":songs,
        "playlists":playlists,
        "albums":albums
    }
    return data
    
@router.get("/color",status_code=200)
def get_coolor_from_image(image_url:str):
    color = get_dominant_color_from_image(image_url=image_url)
    return {"hex_code":color}    
    
def parse_jiosaavn_raw_json(raw_text: str) -> dict:
    try:
        decoded_text = raw_text.encode("utf-8").decode("unicode-escape")
    except Exception:
        decoded_text = raw_text
    pattern = r'\(From "([^"]+)"\)'
    sanitized = re.sub(pattern, r"(From '\1')", decoded_text)
    
    return json.loads(sanitized)


async def fetch_single_song_details(
    client: httpx.AsyncClient, 
    song, 
    search_base_url: str
) -> Optional[dict]:
    # Query with movie if available (highest precision on JioSaavn), else artist
    movie = getattr(song, "movie", "") or ""
    artist = getattr(song, "artist", "") or ""
    
    if movie:
        query = f"{song.song} {movie}".strip()
    elif artist:
        query = f"{song.song} {artist}".strip()
    else:
        query = f"{song.song}".strip()
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if "?" in search_base_url:
            target_url = f"{search_base_url}{query}"
            res = await client.get(target_url, headers=headers, timeout=10.0)
        else:
            res = await client.get(search_base_url, params={"query": query}, headers=headers, timeout=10.0)
        if res.status_code != 200:
            logger.warning(f"Search API returned status {res.status_code} for query: {query}")
            return None
        try:
            data = res.json()
        except Exception:
            data = parse_jiosaavn_raw_json(res.text)
        songs_data = data.get("songs", {}).get("data", [])

        # If movie query yielded no hits, try fallback with artist query
        if not songs_data and movie and artist:
            fallback_query = f"{song.song} {artist}".strip()
            if "?" in search_base_url:
                target_url = f"{search_base_url}{fallback_query}"
                res = await client.get(target_url, headers=headers, timeout=10.0)
            else:
                res = await client.get(search_base_url, params={"query": fallback_query}, headers=headers, timeout=10.0)
            if res.status_code == 200:
                try:
                    data = res.json()
                except Exception:
                    data = parse_jiosaavn_raw_json(res.text)
                songs_data = data.get("songs", {}).get("data", [])

        if not songs_data:
            logger.warning(f"No songs found in search response for: {query}")
            return None

        # Verify that the returned song actually matches the requested song title
        # to avoid JioSaavn fuzzy artist fallbacks (e.g. searching a fake song returning an unrelated hit)
        from services.gemini_service import normalize_title
        norm_req = normalize_title(song.song)
        req_words = set(norm_req.split())

        selected_song = None
        for item in songs_data[:5]:
            norm_item = normalize_title(item.get("title", ""))
            item_words = set(norm_item.split())
            if norm_req == norm_item or norm_req in norm_item or norm_item in norm_req or bool(req_words & item_words):
                selected_song = item
                break

        if not selected_song:
            logger.warning(
                f"No title match on JioSaavn for requested song '{song.song}' (top hit was '{songs_data[0].get('title')}')"
            )
            return None

        song_id = selected_song.get("id")
        if not song_id:
            return None
        song_details = await helper.get_song(song_id, False)
        return song_details

    except httpx.TimeoutException:
        logger.error(f"Timeout while fetching details for song: {query}")
        return None
    except Exception as e:
        logger.error(f"Error processing song '{query}': {str(e)}", exc_info=True)
        return None



@router.post("/recommend", status_code=200)
async def recommend_songs(
    recents: List[HistoryTrack],
    language: str,
    count: int,
    request: Request
):
    recommended_songs = await gemini.generate_recommendations_by_groq(
        history=recents,
        count=count,
        suggestion_language=language
    )
    
    if not recommended_songs:
        return {"message": "No recommendations generated by Gemini", "songs": [], "count": 0}
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        tasks = [
            fetch_single_song_details(
                client=http_client,
                song=song,
                search_base_url=endpoints.search_base_url
            )
            for song in recommended_songs.recommendations
        ]
        results = await asyncio.gather(*tasks)

    valid_songs = [s for s in results if s is not None]

    # Deduplicate resolved songs by song ID / normalized title
    seen_track_ids = set()
    deduped_songs = []
    for s in valid_songs:
        track_id = str(s.get("id") or s.get("song_id") or s.get("title", "")).strip().lower()
        if track_id and track_id not in seen_track_ids:
            seen_track_ids.add(track_id)
            deduped_songs.append(s)

    return {
        "message": "Recommendations Successful !",
        "title": recommended_songs.title,
        "songs": deduped_songs,
        "count": len(deduped_songs)
    }