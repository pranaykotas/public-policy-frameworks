import numpy as np

from ask.embed import embed_texts, EMBED_DIM


def test_embed_texts_empty_returns_correct_shape():
    vectors = embed_texts([])
    assert vectors.shape == (0, EMBED_DIM)


def test_embed_texts_returns_correct_shape():
    vectors = embed_texts(["rent control policy", "semiconductor export controls"])
    assert vectors.shape == (2, EMBED_DIM)


def test_embed_texts_same_topic_more_similar():
    vectors = embed_texts(["rent control reduces housing supply", "rent caps distort the rental market"])
    same_sim = float(np.dot(vectors[0], vectors[1]))
    diff = embed_texts(["rent control reduces housing supply", "GPU export controls to China"])
    diff_sim = float(np.dot(diff[0], diff[1]))
    assert same_sim > diff_sim
