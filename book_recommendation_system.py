import json
import ssl

import numpy as np
from keras.utils import get_file
from tensorflow import keras

from exceptions import IncorrectBookIndex

ssl._create_default_https_context = ssl._create_unverified_context

file = get_file(
    'found_books_filtered.ndjson',
    'https://raw.githubusercontent.com/WillKoehrsen/wikipedia-data-science/master/data/found_books_filtered.ndjson',
    cache_subdir='data'
)

with open(file, 'r') as f:
    books = [json.loads(line) for line in f]

books_with_wikipedia = [book for book in books if 'Wikipedia:' in book[0]]
books = [book for book in books if 'Wikipedia:' not in book[0]]

book_index = {book[0]: idx for idx, book in enumerate(books)}
index_book = {idx: book for book, idx in book_index.items()}

model = keras.models.load_model('book_recommendation_model.h5')

book_layer = model.get_layer('book_embedding')
book_weights = book_layer.get_weights()[0]

book_weights = book_weights / np.linalg.norm(book_weights, axis=1).reshape((-1, 1))


def find_similar_books(name, weights=book_weights, n=10):
    index = book_index
    rindex = index_book

    try:
        dists = np.dot(weights, weights[index[name]])
    except KeyError:
        raise IncorrectBookIndex

    sorted_dists = np.argsort(dists)
    closest = sorted_dists[-n:][:-1]

    recommended_books_data = {}

    for c in reversed(closest):
        recommended_books_data[f'{rindex[c]}'] = f'{int(dists[c] * 100)}%'

    return recommended_books_data
