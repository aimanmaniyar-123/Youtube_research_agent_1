"""
YouTube API Service
Supports BOTH:
- FAST MODE → metadata only
- FULL MODE → transcripts + video statistics
"""

import requests
import re
from typing import Optional, Dict, List
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from config_settings import settings
from utils_logger import get_logger

logger = get_logger("YouTubeAPIService")


class YouTubeAPIService:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.api_key = settings.youtube_api_key
        if not self.api_key:
            raise ValueError("YouTube API key missing")

    # ======================================================================
    # CHANNEL / HANDLE / NAME RESOLUTION
    # ======================================================================
    def _extract_channel_id(self, identifier: str) -> str:
        identifier = identifier.strip()

        # Already UCxxxxxx
        if identifier.startswith("UC") and len(identifier) >= 24:
            return identifier

        # Handle @xxxx
        if identifier.startswith("@"):
            return identifier

        # URLs
        patterns = {
            "channel": r"youtube\.com/channel/([UC][A-Za-z0-9_-]{22})",
            "handle": r"youtube\.com/@([A-Za-z0-9_-]+)",
            "custom": r"youtube\.com/c/([A-Za-z0-9_-]+)",
            "user": r"youtube\.com/user/([A-Za-z0-9_-]+)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, identifier)
            if match:
                extracted = match.group(1)
                if key == "handle":
                    return f"@{extracted}"
                return extracted

        return identifier

    # ======================================================================
    # SEARCH CHANNEL BY HANDLE / NAME
    # ======================================================================
    def get_channel_by_name_or_handle(self, query: str) -> Optional[Dict]:

        query = self._extract_channel_id(query)
        logger.info(f"[YT] Resolving channel: {query}")

        # 1. Direct handle
        if query.startswith("@"):
            url = f"{self.BASE_URL}/channels"
            params = {
                "part": "snippet,statistics,contentDetails",
                "forHandle": query[1:],  # remove "@"
                "key": self.api_key,
            }
            resp = requests.get(url, params=params).json()
            if resp.get("items"):
                return resp["items"][0]

        # 2. Direct UCxxxxxx
        if query.startswith("UC") and len(query) >= 24:
            return self.get_channel_details(query)

        # 3. Fallback search
        url = f"{self.BASE_URL}/search"
        params = {
            "part": "snippet",
            "type": "channel",
            "q": query,
            "maxResults": 5,
            "key": self.api_key,
        }

        resp = requests.get(url, params=params).json()

        for item in resp.get("items", []):
            cid = item["id"]["channelId"]
            return self.get_channel_details(cid)

        return None

    # ======================================================================
    # CHANNEL DETAILS
    # ======================================================================
    def get_channel_details(self, channel_id: str) -> Optional[Dict]:
        url = f"{self.BASE_URL}/channels"
        params = {
            "part": "snippet,statistics,brandingSettings,contentDetails",
            "id": channel_id,
            "key": self.api_key,
        }
        resp = requests.get(url, params=params).json()
        items = resp.get("items", [])
        return items[0] if items else None

    # ======================================================================
    # UPLOADS PLAYLIST
    # ======================================================================
    def _get_uploads_playlist(self, channel_id: str) -> Optional[str]:
        url = f"{self.BASE_URL}/channels"
        params = {
            "part": "contentDetails",
            "id": channel_id,
            "key": self.api_key,
        }
        resp = requests.get(url, params=params).json()
        items = resp.get("items", [])
        if not items:
            return None
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # ======================================================================
    # FAST MODE → METADATA ONLY
    # ======================================================================
    def get_channel_videos(self, channel_id: str, max_results: int = 25) -> List[Dict]:
        playlist_id = self._get_uploads_playlist(channel_id)
        if not playlist_id:
            return []

        url = f"{self.BASE_URL}/playlistItems"
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": max_results,
            "key": self.api_key,
        }

        resp = requests.get(url, params=params).json()
        items = resp.get("items", [])

        videos = []
        for item in items:
            snip = item.get("snippet", {})
            videos.append({
                "id": item.get("contentDetails", {}).get("videoId"),
                "title": snip.get("title"),
                "description": snip.get("description"),
                "publishedAt": snip.get("publishedAt"),
            })

        return videos

    # ======================================================================
    # FULL MODE → VIDEO STATISTICS
    # ======================================================================
    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict]:
        """
        Returns: {video_id: {statistics + snippet}}
        """
        if not video_ids:
            return {}

        url = f"{self.BASE_URL}/videos"
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }

        resp = requests.get(url, params=params).json()
        items = resp.get("items", [])

        out = {}
        for v in items:
            vid = v["id"]
            out[vid] = v
        return out

    # ======================================================================
    # FULL MODE → TRANSCRIPT FETCH
    # ======================================================================
    def get_video_transcript(self, video_id: str) -> Optional[str]:
        """
        Returns transcript text OR raises (handled by orchestrator).
        """
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([entry["text"] for entry in transcript])
            return text.strip()
        except NoTranscriptFound:
            logger.warning(f"No transcript for {video_id}")
            return None
        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for {video_id}")
            return None
        except Exception as e:
            logger.error(f"Transcript fetch failed for {video_id}: {e}")
            return None
