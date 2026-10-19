"""One search index per state (docs/adr/0028).

A state's view holds the passages that apply everywhere plus that state's
own rules, and nothing of any other state. Filtering after a search wasn't
enough once there were two states: a question naming a fish keeps only one
or two slots for shared passages (retriever.arrange_routed), Texas's bait
rules took them, and Georgia's never surfaced for a Georgia angler. In its
own view a state's rules compete only with general content, and IDF is
computed over what that person can actually be shown.

Views are built on first use and kept: all states FishEye hasn't written
rules for share one view (general content only), so there are at most
"covered states + 1" per retriever.
"""
from __future__ import annotations

import threading
import weakref

from app.knowledge import jurisdictions
from app.services.rag.retriever import BM25Retriever, Retriever

_UNCOVERED = "*"
_views: weakref.WeakKeyDictionary[object, dict[str, Retriever]] = weakref.WeakKeyDictionary()
_lock = threading.Lock()


def for_state(retr: Retriever, state: str) -> Retriever | None:
    """`retr` restricted to what applies in `state`, or None for a
    retriever it doesn't know how to restrict (the caller then filters)."""
    group = state if (j := jurisdictions.get(state)) and j.covered else _UNCOVERED
    with _lock:
        cached = _views.get(retr, {}).get(group)
    if cached is not None:
        return cached
    view = _build(retr, state)
    if view is not None:
        with _lock:
            _views.setdefault(retr, {})[group] = view
    return view


def _build(retr: Retriever, state: str) -> Retriever | None:
    passages = getattr(retr, "passages", None)
    if passages is None:
        return None
    keep = [i for i, p in enumerate(passages) if jurisdictions.applies(p.region, state)]
    if len(keep) == len(passages):
        return retr
    subset = [passages[i] for i in keep]
    if isinstance(retr, BM25Retriever):
        return BM25Retriever(subset)
    from app.services.rag.hybrid import HybridRetriever  # needs numpy; only when hybrid is in use

    if isinstance(retr, HybridRetriever):
        # The passage vectors are reused, not re-encoded.
        return HybridRetriever(BM25Retriever(subset), retr.embedder, retr._vecs[keep])
    return None
