import os
import pickle
import logging
from rank_bm25 import BM25Okapi
import spacy 
logger = logging.getLogger(__name__)
nlp = spacy.load("de_core_news_sm")

def extract_texts_from_ground_truth(ground_truth):
    return [item["text"] for item in ground_truth.get("all_texts", [])]

def tokenize(text):
    return [token.text.lower() for token in nlp(text) if not token.is_space]

def build_bm25_index(texts):
    """
    Builds a BM25 index using NLTK tokenization.
    """
    tokenized_texts = [tokenize(t) for t in texts]
    return BM25Okapi(tokenized_texts)

def save_index(index, path):
    with open(path, "wb") as f:
        pickle.dump(index, f)

def load_index(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def get_or_build_index(ground_truth, pickle_path):
    if os.path.exists(pickle_path):
        logger.info(f"Loading BM25 index from {pickle_path}")
        return load_index(pickle_path)
    logger.info(f"Building BM25 index and saving to {pickle_path}")
    texts = extract_texts_from_ground_truth(ground_truth)
    index = build_bm25_index(texts)
    save_index(index, pickle_path)
    return index
