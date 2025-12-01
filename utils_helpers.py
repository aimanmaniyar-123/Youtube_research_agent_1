# utils_helpers.py
import re
import aiohttp
from utils_logger import get_logger

logger = get_logger("utils")


def extract_channel_from_text(text: str) -> str:
    """Extract handle, channel id or short name from user input."""
    if not text:
        return ""

    text = text.strip()

    # handle
    m = re.search(r"@([A-Za-z0-9_]+)", text)
    if m:
        handle = f"@{m.group(1)}"
        logger.info(f"extract_channel_from_text → handle={handle}")
        return handle

    # url
    url_m = re.search(r"(https?://[^\s]+)", text)
    if url_m:
        url = url_m.group(1)
        h = re.search(r"/@([A-Za-z0-9_\-\.]+)", url)
        if h:
            return f"@{h.group(1)}"
        c = re.search(r"/channel/([A-Za-z0-9_-]+)", url)
        if c:
            return c.group(1)

    # short text guess
    words = text.split()
    if len(words) <= 5:
        guess = " ".join(words)
        logger.info(f"extract_channel_from_text → guess channel name={guess}")
        return guess

    logger.info("extract_channel_from_text → fallback to original text")
    return text


async def get_transcript_or_empty(video_id: str) -> str:
    """
    FULL MODE (metadata-only) - intentionally returns empty string.
    We do metadata-based embeddings only (title + description).
    """
    return ""


async def fetch_json(url: str, params=None, headers=None, timeout=10):
    """Async GET returning JSON or None."""
    if params is None:
        params = {}
    if headers is None:
        headers = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    logger.warning(f"fetch_json failed {url} → status {resp.status}")
                    return None
                return await resp.json()
    except Exception as e:
        logger.error(f"fetch_json error for {url}: {e}")
        return None
