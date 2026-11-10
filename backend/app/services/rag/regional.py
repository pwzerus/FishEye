"""One search index per state (docs/adr/0028).

A state's view holds the passages that apply everywhere plus that state's
own rules, and nothing of any other state. Filtering after a search wasn't
enough once there were two states: a question naming a fish keeps only one
or two slots for shared passages (retriever.arrange_routed), Texas's bait
rules took them, and Georgia's never surfaced for a Georgia angler. In its
own view a state's rules compete only with general content, and IDF is
computed over what that person can actually be shown.

Views are built on first use and kept: any state FishEye has written nothing
for shares one view (general content only), so there are at most "states with
something written + 1" per retriever.
"""
from __future__ import annotations

import threading
import weakref

from app.knowledge import jurisdictions
from app.services.rag.retriever import BM25Retriever, Retriever

_UNCOVERED = "*"
_NO_STATE = ""
_views: weakref.WeakKeyDictionary[object, dict[str, Retriever]] = weakref.WeakKeyDictionary()
_lock = threading.Lock()


def for_state(retr: Retriever, state: str | None) -> Retriever | None:
    """`retr` restricted to what applies in `state` (None: no state given,
    jurisdictions.applies), or None for a retriever it doesn't know how
    to restrict (the caller then filters)."""
    if state is None:
        group = _NO_STATE
    else:
        written = (j := jurisdictions.get(state)) and (j.covered or j.license_topic)
        group = state if written else _UNCOVERED
    with _lock:
        cached = _views.get(retr, {}).get(group)
    if cached is not None:
        return cached
    view = _build(retr, state)
    if view is not None:
        with _lock:
            _views.setdefault(retr, {})[group] = view
    return view


def _build(retr: Retriever, state: str | None) -> Retriever | None:
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
        return HybridRetriever(BM25Retriever(subset), retr.embedder, retr._vecs[keep], retr.ways)
    return None
