"""BM25 Lexical Retriever

Implements Okapi BM25 with Robertson-Spärck Jones IDF and robust tokenization
preserving technical codes, hyphenated terms, decimal numbers, and units.
"""

import math
import re
from typing import List, Dict, Tuple, Optional
from collections import Counter

# Tokenizer regex: matches technical terms (e.g., RS-485, IP-67, v2.1, 0.75MPa), numbers, or words
TOKEN_PATTERN = re.compile(
    r'[a-zA-Z0-9]+(?:[-_.:/][a-zA-Z0-9]+)+|\d+(?:\.\d+)?|[a-zA-Z]+'
)

def tokenize(text: str) -> List[str]:
    """
    Tokenizes text while preserving technical identifiers, version numbers,
    measurements, and abbreviations in lowercase.
    """
    if not text:
        return []
    tokens = TOKEN_PATTERN.findall(text)
    # Strip any trailing punctuation that might cling to tokens
    cleaned = []
    for t in tokens:
        c = t.strip("._-/:").lower()
        if c:
            cleaned.append(c)
    return cleaned

class BM25:
    """
    Okapi BM25 indexer and ranker.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size: int = 0
        self.avg_doc_len: float = 0.0
        self.doc_lengths: List[int] = []
        self.doc_freqs: Dict[str, int] = {}
        self.term_freqs: List[Counter] = []
        self.doc_ids: List[str] = []

    def fit(self, doc_ids: List[str], texts: List[str]) -> None:
        """
        Builds the BM25 index from a corpus of documents/chunks.
        """
        self.doc_ids = doc_ids
        self.corpus_size = len(texts)
        self.doc_lengths = []
        self.term_freqs = []
        self.doc_freqs = {}

        if self.corpus_size == 0:
            self.avg_doc_len = 0.0
            return

        total_length = 0
        for text in texts:
            tokens = tokenize(text)
            length = len(tokens)
            self.doc_lengths.append(length)
            total_length += length
            
            tf = Counter(tokens)
            self.term_freqs.append(tf)

            for term in tf.keys():
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avg_doc_len = total_length / self.corpus_size if self.corpus_size > 0 else 0.0

    def idf(self, term: str) -> float:
        """
        Robertson-Spärck Jones IDF with smoothing (+1 inside log ensures non-negative weights).
        """
        n_q = self.doc_freqs.get(term, 0)
        return math.log(1.0 + (self.corpus_size - n_q + 0.5) / (n_q + 0.5))

    def score(self, query: str) -> List[Tuple[str, float]]:
        """
        Scores all indexed documents against a query.
        Returns list of (doc_id, score) pairs.
        """
        if self.corpus_size == 0 or self.avg_doc_len == 0.0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return [(d_id, 0.0) for d_id in self.doc_ids]

        scores = [0.0] * self.corpus_size

        for term in query_tokens:
            if term not in self.doc_freqs:
                continue

            term_idf = self.idf(term)

            for i in range(self.corpus_size):
                tf = self.term_freqs[i].get(term, 0)
                if tf == 0:
                    continue

                doc_len = self.doc_lengths[i]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[i] += term_idf * (numerator / denominator)

        return list(zip(self.doc_ids, scores))
