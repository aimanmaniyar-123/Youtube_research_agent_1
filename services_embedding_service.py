# services_embedding_service.py
import os
import numpy as np
from fastembed import TextEmbedding
from utils_logger import get_logger

logger = get_logger("embedding_service")

_EMBED_MODEL_DEFAULT = os.getenv("SENTENCE_TRANSFORMERS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_EMBED_DIM = 384

_embedder = None


def get_embedding_service(config: dict = None):
    global _embedder
    if _embedder is None:
        model = None
        if config and isinstance(config, dict):
            model = config.get("model")
        model_name = model or _EMBED_MODEL_DEFAULT
        logger.info(f"Loading embedding model: {model_name}")
        _embedder = TextEmbedding(model_name)
    return _embedder


def embed_text(text: str):
    """
    Returns numpy array (dim,) or None.
    Fix: FastEmbed returns a generator → wrap with list().
    """
    global _embedder
    if not _embedder:
        get_embedding_service()
    if not text or not text.strip():
        return None

    # FastEmbed returns a generator → convert to list
    try:
        emb_list = list(_embedder.embed([text]))
        if not emb_list:
            return None

        emb = emb_list[0]
        return np.array(emb, dtype=np.float32)

    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None
