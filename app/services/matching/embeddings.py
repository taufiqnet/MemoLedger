import numpy as np
from typing import List, Optional

class VectorEmbedder:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorEmbedder, cls).__new__(cls)
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            except Exception:
                cls._model = None
        return cls._instance

    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a text string into a 384-dimensional vector.
        If sentence-transformers is unavailable, generates a deterministic normalized hash vector.
        """
        if not text:
            return [0.0] * 384

        if self._model:
            try:
                emb = self._model.encode(text, convert_to_numpy=True)
                return emb.tolist()
            except Exception:
                pass

        # Deterministic fallback embedding based on character bigram hashing
        vec = np.zeros(384, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words):
            h = hash(word) % 384
            vec[h] += 1.0 / (i + 1.0)
            for j in range(len(word) - 1):
                bi_h = hash(word[j:j+2]) % 384
                vec[bi_h] += 0.5
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))


vector_embedder = VectorEmbedder()
