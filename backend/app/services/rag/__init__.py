"""Question answering over the reviewed fish guides (docs/adr/0014-rag-over-species-guides.md).

- chunking.py  — split each guide into small, self-describing passages
- retriever.py — rank passages for a question (BM25 + species routing)
- ask.py       — prompt, validate, retry, fall back; the part a user calls
"""
