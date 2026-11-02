from fastembed import TextEmbedding

model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def embed_texts(texts):
    return [vector.tolist() for vector in model.embed(texts)]
