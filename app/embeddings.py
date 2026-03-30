
from sentence_transformers import SentenceTransformer


def embed_texts(texts):

    model = SentenceTransformer("all-MiniLM-L6-v2")

    return model.encode(texts)