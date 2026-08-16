from __future__ import annotations

import numpy as np

EMBED_DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME, backend="onnx")
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of strings into L2-normalized vectors via a local model."""
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)
    model = _get_model()
    return model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > BATCH_SIZE,
    ).astype(np.float32)
