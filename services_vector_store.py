# services_vector_store.py
import hnswlib
import numpy as np
from typing import List, Tuple
from utils_logger import get_logger

logger = get_logger("vector_store")

class HNSWVectorStore:
    def __init__(self, dim=384, max_elements=5000):
        self.dim = dim
        self.max_elements = max_elements
        self.index = hnswlib.Index(space='cosine', dim=dim)
        logger.info("Initializing HNSW index...")
        self.index.init_index(max_elements=max_elements, ef_construction=100, M=32)
        self.index.set_ef(64)
        self.ids = []

    def add(self, embedding: np.ndarray, video_id: str):
        if embedding is None:
            return
        idx = len(self.ids)
        self.ids.append(video_id)
        self.index.add_items(embedding.reshape(1, -1), np.array([idx]))

    def search(self, embedding: np.ndarray, k=5) -> List[Tuple[str, float]]:
        if embedding is None or len(self.ids) == 0:
            return []
        labels, distances = self.index.knn_query(embedding.reshape(1, -1), k=k)
        results = []
        for i, d in zip(labels[0], distances[0]):
            if i < len(self.ids):
                results.append((self.ids[i], float(d)))
        return results

_vector_store_instance = None
def get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = HNSWVectorStore(dim=384, max_elements=5000)
    return _vector_store_instance
