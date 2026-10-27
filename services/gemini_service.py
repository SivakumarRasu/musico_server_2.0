import logging
import os
import random
import re
import time
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import AsyncGroq
from pydantic import ValidationError

from pydantic_shemas.recommandation_schemas import GeminiRecommendationSchema, GeminiTrack, HistoryTrack

load_dotenv()


def normalize_title(title: str) -> str:
    """Normalize song title to detect duplicates and history matches."""
    if not title:
        return ""
    # Remove parenthetical / bracketed info like "(From Master)", "[Remix]"
    cleaned = re.sub(r"\(.*?\)|\[.*?\]", "", title.lower())
    # Remove common audio/video/filler tags
    cleaned = re.sub(r"\b(feat|ft|from|ost|audio|video|lyric|lyrics|remix|reprise|version)\b.*", "", cleaned)
    # Remove punctuation and extra whitespace
    cleaned = re.sub(r"[^a-z0-9\s]", "", cleaned)
    return " ".join(cleaned.split())


class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY", ""))
        self.logger = logging.getLogger("uvicorn.error")

    
    
    async def generate_recommandations_by_gemini(
        self, history: list, count: int, suggestion_language: str
    ):
        history_summary = "\n".join(
            [f"- {getattr(t, 'title', str(t))} by {getattr(t, 'artist', 'Unknown')}" for t in history]
        )

        prompt = f"""
You are an expert music recommendation engine.

Your task is to analyze the user's listening history and generate personalized
music recommendations.

## User Listening History
{history_summary}

## Request Details
- Preferred language: {suggestion_language}
- Number of recommendations required: {count}

## Instructions

1. Carefully analyze the user's listening patterns, including:
   - Frequently listened artists
   - Genres and subgenres
   - Mood and emotional tone
   - Energy level and tempo preferences
   - Musical style and overall vibe

2. Recommend exactly {count} DISTINCT songs that best match the user's
   listening preferences.

3. Prioritize songs that are:
   - Popular, trending, or currently gaining significant listener attention
   - Highly relevant to the user's established musical taste
   - Appropriate for the requested language: {suggestion_language}

4. STRICTLY DO NOT recommend:
   - Songs already present in the user's listening history
   - Duplicate songs
   - Multiple versions/remixes of the same song unless clearly necessary

5. Include a balanced mix of:
   - Well-known popular tracks
   - Trending songs
   - Relevant discoveries that closely match the user's vibe

6. Create a short, stylish, and engaging title for the recommendation playlist.
   The title should reflect the user's listening mood and overall vibe.

## Output Requirements

Return ONLY valid JSON in the following format:

{{
    "title": "Short and stylish recommendation title",
    "description": "A short description explaining the vibe of this recommendation",
    "recommendations": [
        {{
            "song": "Song Name",
            "artist": "Artist Name",
            "language": "{suggestion_language}",
            "reason": "Brief reason why this song matches the user's taste"
        }}
    ]
}}

Important:
- Return exactly {count} songs.
- Ensure every song is distinct.
- Never include songs already present in the listening history.
- Prioritize accurate song titles and artist names.
- Do not include markdown, explanations, or any text outside the JSON response.
"""

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiRecommendationSchema,
                    temperature=0.7,
                ),
            )
            
            

            parsed = GeminiRecommendationSchema.model_validate_json(response.text)
            self.logger.info(f"Gemini successfully returned {len(parsed.recommendations)} songs.")
            return parsed

        except Exception as e:
            self.logger.error(f"Gemini generation error: {str(e)}", exc_info=True)
            return []
    
    async def generate_recommendations(
        self,
        history: list,
        count: int,
        suggestion_language: str
    ):
        # 1. Parse and extract history items
        history_items = []
        for t in history:
            title = getattr(t, "title", None) or (t.get("title") if isinstance(t, dict) else str(t))
            artist = getattr(t, "artist", None) or (t.get("artist") if isinstance(t, dict) else "Unknown")
            if title:
                history_items.append({"title": title.strip(), "artist": artist.strip()})

        history_summary = "\n".join(
            [f"- \"{item['title']}\" by {item['artist']}" for item in history_items]
        )
        history_titles = [item["title"] for item in history_items if item["title"]]
        history_exclusions = ", ".join([f'"{t}"' for t in history_titles])

        # 2. Dynamic YouTube-style vibe mode rotation & seed jitter to eliminate repetition
        vibe_modes = [
            "Vibe Continuity: Seamlessly match the energy, acoustic tempo, and emotional mood of the recent tracks",
            "Artist Orbit: Songs by frequent collaborators, co-singers, composers, and similar style contemporaries",
            "Trending Discovery: Viral, trending, and chart-topping hits in this language/genre that fit the vibe",
            "Deep Cuts & Melodies: Highly rated crowd favorites, nostalgic gems, and non-obvious tracks fitting the taste profile",
            "High-Voltage Energy: Fast-paced, punchy, upbeat anthems with similar driving rhythm and production"
        ]
        selected_vibe = random.choice(vibe_modes)
        variety_seed = int(time.time() * 1000) % 100000

        # Over-fetch candidates so deduplication leaves exactly the requested count
        candidate_count = max(count + 5, 12)

        prompt = f"""You are the music recommendation algorithm behind YouTube Music's "Up Next" and "Radio Mix".
Generate a personalized, non-repetitive list of {candidate_count} distinct songs in {suggestion_language} based on the user's listening history.

### USER'S RECENT LISTENING HISTORY:
{history_summary}

### SESSION PARAMETERS:
- Preferred Language: {suggestion_language}
- Target Vibe Direction: {selected_vibe}
- Session Variety Seed: {variety_seed}

### YOUTUBE MUSIC RECOMMENDATION LOGIC:
1. Core Taste (~40%): Real, high-quality songs matching the vibe and genre of their history, but NEVER repeating songs from the history list.
2. Adjacent Artists & Collaborators (~40%): Songs by singers, composers, and artists connected or similar to those in the history.
3. Fresh Discovery (~20%): Viral, trending, or highly celebrated songs in {suggestion_language} matching the acoustic energy.
4. Artist Variety Cap: Maximum 2 songs per artist across the entire queue. Do NOT saturate the list with a single artist.

### CRITICAL RULES (ZERO HALLUCINATIONS & ZERO DUPLICATES):
- EVERY SINGLE SONG MUST BE A REAL, COMMERCIALLY RELEASED TRACK THAT ACTUALLY EXISTS ON STREAMING PLATFORMS (JioSaavn, Spotify).
- ABSOLUTELY DO NOT INVENT OR HALLUCINATE FAKE SONG NAMES.
- For every song, provide the ACCURATE movie/album name and correct primary music director or artist.
- ABSOLUTELY DO NOT recommend any song already in the user's listening history: [{history_exclusions}].
- Every song in the recommendations array MUST be unique. Zero duplicates allowed.

### JSON OUTPUT FORMAT:
You must respond with a raw JSON object only. Do NOT wrap in markdown fences (no ```json). Do NOT add text or explanation outside the JSON object.
Schema:
{{
  "title": "Short stylish YouTube-style mix title (e.g., Tamil Melodic Vibe Radio)",
  "recommendations": [
    {{
      "song": "Exact Real Song Name",
      "movie": "Accurate Movie or Album Name",
      "artist": "True Music Director / Primary Artist",
      "language": "{suggestion_language}"
    }}
  ]
}}"""

        response_text = None

        # 1. Primary: Google Gemini (native knowledge of Indian cinema discographies)
        gemini_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
        for g_model in gemini_models:
            try:
                res = await self.client.aio.models.generate_content(
                    model=g_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                if res.text:
                    clean = res.text.strip()
                    if clean.startswith("```"):
                        clean = re.sub(r"^```(?:json)?\s*", "", clean)
                        clean = re.sub(r"\s*```$", "", clean).strip()
                    response_text = clean
                    self.logger.info(f"Recommendation succeeded using Google Gemini: {g_model}")
                    break
            except Exception as ge:
                self.logger.warning(f"Gemini model {g_model} failed: {ge}, trying fallback...")

        # 2. Fallback: Groq openai/gpt-oss-120b (reliable creative generative LLM)
        if not response_text:
            groq_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
            for model_name in groq_models:
                try:
                    response = await self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a professional music recommendation engine modeled after YouTube Music. "
                                    "You must output raw JSON only matching the schema. All songs must be real tracks."
                                ),
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        temperature=0.7,
                        response_format={"type": "json_object"},
                    )
                    raw_content = response.choices[0].message.content
                    if raw_content:
                        clean_content = raw_content.strip()
                        if clean_content.startswith("```"):
                            clean_content = re.sub(r"^```(?:json)?\s*", "", clean_content)
                            clean_content = re.sub(r"\s*```$", "", clean_content).strip()
                        response_text = clean_content
                        self.logger.info(f"Recommendation succeeded using Groq model: {model_name}")
                        break
                except Exception as model_err:
                    self.logger.warning(
                        f"Groq model {model_name} failed: {model_err}, trying next model..."
                    )



        if not response_text:
            self.logger.error("All Groq recommendation models failed.")
            return []

        try:
            parsed = GeminiRecommendationSchema.model_validate_json(response_text)

            # Code-level Multi-Tier Deduplication
            normalized_history = {normalize_title(t): True for t in history_titles if t}
            seen_titles = set()
            artist_counts = {}
            deduped_recommendations = []

            # Pass 1: Strict deduplication with artist cap (max 2 songs per artist)
            for track in parsed.recommendations:
                norm_title = normalize_title(track.song)
                if not norm_title:
                    continue
                # 1. Skip if already in listening history
                if norm_title in normalized_history:
                    self.logger.info(f"Filtered out history song: {track.song}")
                    continue
                # 2. Skip if duplicate within recommendations
                if norm_title in seen_titles:
                    self.logger.info(f"Filtered out duplicate song: {track.song}")
                    continue
                # 3. Cap per artist
                artist_key = track.artist.strip().lower()
                if artist_counts.get(artist_key, 0) >= 2:
                    continue

                seen_titles.add(norm_title)
                artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1
                deduped_recommendations.append(track)

                if len(deduped_recommendations) >= count:
                    break

            # Pass 2: If we still need more tracks to fulfill count, relax the artist cap
            if len(deduped_recommendations) < count:
                for track in parsed.recommendations:
                    norm_title = normalize_title(track.song)
                    if not norm_title or norm_title in normalized_history or norm_title in seen_titles:
                        continue
                    seen_titles.add(norm_title)
                    deduped_recommendations.append(track)
                    if len(deduped_recommendations) >= count:
                        break

            parsed.recommendations = deduped_recommendations
            self.logger.info(
                f"Groq successfully returned {len(parsed.recommendations)} unique recommendations."
            )
            self.logger.info(
                f"Recommended Songs returned {parsed.recommendations}"
            )
            return parsed

        except ValidationError as e:
            self.logger.error(
                f"Groq response validation error: {str(e)}",
                exc_info=True,
            )
            return []

        except Exception as e:
            self.logger.error(
                f"Groq generation error: {str(e)}",
                exc_info=True,
            )
            return []

    # Provide alias for routes calling generate_recommendations_by_groq
    generate_recommendations_by_groq = generate_recommendations
