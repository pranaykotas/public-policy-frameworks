import numpy as np

from ask.embed import embed_texts


def test_embed_texts_returns_correct_shape():
    vectors = embed_texts(["rent control policy", "semiconductor export controls"])
    assert vectors.shape == (2, 384)


def test_embed_texts_identical_strings_are_near_identical():
    vectors = embed_texts(["rent control reduces housing supply", "rent control reduces housing supply"])
    similarity = float(np.dot(vectors[0], vectors[1]))
    assert similarity > 0.99


def test_embed_texts_unrelated_strings_are_less_similar_than_identical():
    vectors = embed_texts(["rent control reduces housing supply", "GPU export controls to China"])
    same_topic = embed_texts(["rent control reduces housing supply", "rent caps distort the rental market"])
    unrelated_similarity = float(np.dot(vectors[0], vectors[1]))
    same_topic_similarity = float(np.dot(same_topic[0], same_topic[1]))
    assert same_topic_similarity > unrelated_similarity
