"""Retrieval eval set for guide Q&A (services/rag/).

Each case is a question phrased the way a beginner would ask it, and the
passages that would answer it. A case is a hit if ANY relevant passage is
in the top K — several passages often answer the same question equally
well (both crappie bait lists), and punishing the retriever for picking
either one would measure the label, not the retrieval.

Written before tuning, and kept honest: questions use nicknames ("sand
bass", "bream"), paraphrases ("tie on", "feed on"), and a few that lexical
matching is expected to find hard. The ones that still miss are listed in
the report instead of being quietly reworded until they pass — that list is
the evidence for (or against) adding an embedding retriever later.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RagCase:
    id: str
    question: str
    relevant: frozenset[str]
    species_context: str | None = None  # asked from a fish's own page
    note: str = ""


def _c(id: str, question: str, *relevant: str, context: str | None = None, note: str = "") -> RagCase:
    return RagCase(id, question, frozenset(relevant), context, note)


# Off-topic questions: the right retrieval is nothing at all.
OFF_TOPIC: tuple[str, ...] = (
    "what is the capital of france",
    "how do I change a car tire",
    "recommend a good pizza place",
)

CASES: tuple[RagCase, ...] = (
    # --- bait and lures ---
    _c("crappie-bait", "what bait for crappie", "white-crappie#live_baits", "black-crappie#live_baits"),
    _c("lmb-lure", "best lure for largemouth", "largemouth-bass#lures"),
    _c("bluegill-bait", "what should I put on the hook for bluegill", "bluegill#live_baits"),
    _c("catfish-bait", "what's a good bait for channel cats", "channel-catfish#live_baits"),
    _c("bluecat-bait", "what do people use to catch big blue catfish", "blue-catfish#live_baits", "blue-catfish#overview"),
    _c("sandbass-lure", "what lures work on sand bass", "white-bass#lures", note="Texas nickname"),
    _c("striper-live", "live bait for stripers", "striped-bass#live_baits", "striped-bass#setup-2"),
    _c("bream", "bream bait", "bluegill#live_baits", note="Southern nickname"),
    # --- rigs and tackle ---
    _c("bluegill-hook", "what hook size for bluegill", "bluegill#setup-1", "bluegill#setup-2", "bluegill#setup-3"),
    _c("catfish-gear", "what gear do I need for catfish", "channel-catfish#setup-1", "channel-catfish#setup-2", "blue-catfish#setup-1", "blue-catfish#setup-2"),
    _c("pond-cat-rig", "how do I rig for catfish in a city pond", "channel-catfish#setup-1"),
    _c("crappie-bobber", "how deep should I set a bobber for crappie", "white-crappie#setup-1", "black-crappie#setup-1"),
    _c("texas-rig", "how do I texas rig a worm", "largemouth-bass#setup-2"),
    _c("striper-rod", "what rod for stripers", "striped-bass#setup-1", "striped-bass#setup-2", "striped-bass#setup-3"),
    _c("bluecat-line", "what line strength for blue catfish", "blue-catfish#setup-1", "blue-catfish#setup-2"),
    _c("kid-pole", "easiest setup for a kid who has never fished", "bluegill#setup-1", "bluegill#setup-2", note="no species named"),
    _c("spotted-finesse", "spotted bass finesse rig", "spotted-bass#setup-1", "spotted-bass#setup-2"),
    # --- where and when ---
    _c("bluegill-summer", "where do bluegill hang out in summer", "bluegill#where_and_when"),
    _c("whitebass-run", "when do white bass run", "white-bass#where_and_when"),
    _c("crappie-where", "where should I look for crappie", "white-crappie#where_and_when", "black-crappie#where_and_when", "white-crappie#overview"),
    _c("lmb-cover", "where do largemouth hide", "largemouth-bass#where_and_when", "largemouth-bass#overview"),
    _c("shad-depth", "how deep are threadfin shad", "threadfin-shad#where_and_when"),
    # --- diet and identification ---
    _c("sandbass-eat", "what do sand bass eat", "white-bass#diet"),
    _c("bluecat-diet", "what do they feed on", "blue-catfish#diet", context="blue-catfish", note="asked from the fish's page"),
    _c("shad-id", "how do I tell gizzard shad from threadfin shad", "gizzard-shad#identification", "threadfin-shad#identification"),
    # --- bait fish and rules ---
    _c("get-shad", "how do I catch shad to use as bait", "gizzard-shad#how_to_get", "threadfin-shad#how_to_get"),
    _c("cast-net", "how big a cast net can I use", "gizzard-shad#how_to_get", "threadfin-shad#how_to_get"),
    _c("move-bait", "can I bring live bait from one lake to another", "all-fish#bait_rules"),
    _c("gamefish-bait", "is it legal to use a small bass as bait", "all-fish#bait_rules"),
    _c("shad-for-what", "what is gizzard shad good bait for", "gizzard-shad#bait_for"),
)
