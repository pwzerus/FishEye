"""Spanish questions.

The guides are English, and Ask's search is decided by English words
(retriever.py: the topic gate, fish names, how-to questions). A Spanish
question is put into those words first: "¿Qué carnada uso para bagre en el
río?" is searched as "what bait use for catfish in the river". The answer
quotes the guides, as it does for a Chinese question (zh.py), with
FishEye's own sentences in Spanish (replies.py).

The glossary is Mexican and US Spanish as anglers say it (carnada, señuelo,
acocil, lobina, mojarra), written by hand: a fishing word machine
translation gets wrong is a question that finds nothing. Matching ignores
accents and case, longest phrase first.
"""
from __future__ import annotations

import re
import unicodedata

from app.services.rag.zh import has_chinese

# Spanish phrase -> the English words the guides use for it.
GLOSSARY: dict[str, str] = {
    # fish
    "lobina negra": "largemouth bass",
    "lobina boca grande": "largemouth bass",
    "lobina de boca grande": "largemouth bass",
    "perca americana": "largemouth bass",
    "lobina de boca chica": "smallmouth bass",
    "lobina boca chica": "smallmouth bass",
    "lobina manchada": "spotted bass",
    "lobina de guadalupe": "guadalupe bass",
    "lobina blanca": "white bass",
    "lobina rayada": "striped bass",
    "lobina hibrida": "hybrid striped bass",
    "lobina rayada hibrida": "hybrid striped bass",
    "lobina": "bass",
    "robalo": "bass",
    "bagre de canal": "channel catfish",
    "bagre azul": "blue catfish",
    "bagre cabeza plana": "flathead catfish",
    "bagre piltonte": "flathead catfish",
    "bagre": "catfish",
    "pez gato": "catfish",
    "crappie blanco": "white crappie",
    "crappie negro": "black crappie",
    "mojarra de agallas azules": "bluegill",
    "pez sol de agallas azules": "bluegill",
    "mojarra de oreja roja": "redear sunfish",
    "mojarra": "bluegill sunfish",
    "pez sol": "sunfish",
    "trucha arcoiris": "rainbow trout",
    "trucha arco iris": "rainbow trout",
    "trucha cafe": "brown trout",
    "trucha marron": "brown trout",
    "trucha": "trout",
    "corvina de agua dulce": "freshwater drum",
    "corvina": "freshwater drum",
    "carpa comun": "common carp",
    "carpa": "carp",
    "sardina molleja": "gizzard shad",
    "sardina maya": "threadfin shad",
    "sardina": "shad",
    "lucioperca": "walleye",
    "lucio": "northern pike",
    "perca amarilla": "yellow perch",
    "salmon": "salmon",
    "pejelagarto": "gar",
    "catan": "gar",
    "tilapia": "tilapia",
    # bait
    "carnada viva": "live bait",
    "carnada": "bait",
    "carnadas": "bait",
    "cebo": "bait",
    "cebos": "bait",
    "carnada apestosa": "stink bait",
    "lombriz de tierra": "worm nightcrawler",
    "lombrices": "worms nightcrawlers",
    "lombriz": "worm nightcrawler",
    "gusanos de cera": "wax worms",
    "gusano de cera": "wax worm",
    "gusanos de harina": "mealworms",
    "gusanos": "worms",
    "gusano": "worm",
    "grillos": "crickets",
    "grillo": "cricket",
    "chapulines": "grasshoppers",
    "chapulin": "grasshopper",
    "saltamontes": "grasshopper",
    "acociles": "crayfish",
    "acocil": "crayfish",
    "cangrejo de rio": "crayfish",
    "langostinos": "crayfish",
    "camarones": "shrimp",
    "camaron": "shrimp",
    "higado de pollo": "chicken liver",
    "higado": "liver",
    "salchicha": "hot dog",
    "queso": "cheese",
    "maiz": "corn",
    "elote": "corn",
    "masa": "dough bait",
    "pececillos": "minnows",
    "pececillo": "minnow",
    "pescaditos": "minnows",
    "pescadito": "minnow",
    "carnada en trozos": "cut bait",
    # lures and tackle
    "senuelos": "lures",
    "senuelo": "lure",
    "plasticos suaves": "soft plastics",
    "plastico suave": "soft plastic",
    "cucharillas": "spinners",
    "cucharilla": "spinner",
    "cucharas": "spoons",
    "cuchara": "spoon",
    "superficie": "topwater",
    "anzuelo circular": "circle hook",
    "anzuelos": "hooks",
    "anzuelo": "hook",
    "tamano de anzuelo": "hook size",
    "numero de anzuelo": "hook size",
    "canas": "rods",
    "cana": "rod",
    "carretes": "reels",
    "carrete": "reel",
    "linea trenzada": "braid line",
    "trenzada": "braid",
    "fluorocarbono": "fluorocarbon",
    "monofilamento": "monofilament",
    "linea": "line",
    "hilo": "line",
    "sedal": "line",
    "boyas": "bobbers",
    "boya": "bobber",
    "corcho": "bobber",
    "flotador": "bobber",
    "plomos": "sinkers split shot",
    "plomo": "sinker split shot",
    "plomada": "sinker",
    "destorcedor": "swivel",
    "lider": "leader",
    "nudos": "knots",
    "nudo": "knot",
    "freno": "drag",
    "red": "net",
    "atarraya": "cast net",
    # doing it
    "como pesco": "how catch",
    "como se pesca": "how catch",
    "como pescar": "how catch",
    "como atrapo": "how catch",
    "pescar": "catch fish",
    "pesco": "catch",
    "pescas": "catch",
    "pescan": "catch",
    "pesca": "fishing",
    "atrapar": "catch",
    "sacar": "catch",
    "lanzar": "cast",
    "lance": "cast",
    "lanzo": "cast",
    "amarrar": "tie",
    "amarro": "tie",
    "atar": "tie",
    "limpiar": "clean",
    "limpio": "clean",
    "filetear": "fillet",
    "filete": "fillet",
    "escamar": "scale",
    "quitar la piel": "skin",
    "cocinar": "cook",
    "cocino": "cook",
    "freir": "fry",
    "congelar": "freeze",
    "soltar": "release",
    "liberar": "release",
    "quedarme con": "keep",
    "quedarse con": "keep",
    "me puedo quedar": "keep",
    "puedo quedarme": "keep",
    "quedarme": "keep",
    "quedar": "keep",
    "quedo": "keep",
    "llevarme": "keep",
    "desangrar": "bleed",
    "medir": "measure",
    # rules and safety
    "licencia de pesca": "fishing license",
    "licencia": "license",
    "permiso de pesca": "fishing license",
    "permiso": "license",
    "limite diario": "daily limit",
    "limites": "limits",
    "limite": "limit",
    "tamano minimo": "minimum size",
    "tamano": "size",
    "medida": "size",
    "reglamento": "regulations rules",
    "reglas": "rules",
    "regla": "rule",
    "ley": "law rules",
    "chaleco salvavidas": "life jacket",
    "chaleco": "life jacket",
    "edad": "age",
    # where and when
    "orilla": "bank shore",
    "muelle": "dock pier",
    "muelles": "docks",
    "lago": "lake",
    "lagos": "lakes",
    "presa": "reservoir",
    "rio": "river",
    "arroyo": "creek",
    "estanque": "pond",
    "noche": "night",
    "amanecer": "dawn morning",
    "manana": "morning",
    "atardecer": "dusk evening",
    "tarde": "evening",
    "invierno": "winter",
    "verano": "summer",
    "primavera": "spring",
    "otono": "fall",
    "viento": "wind",
    "lluvia": "rain",
    "frente frio": "cold front",
    "frente": "front",
    "agua turbia": "muddy water",
    "agua clara": "clear water",
    "profundidad": "depth deep",
    "hondo": "deep",
    "temporada": "season",
    "epoca": "season",
    "hora": "time",
    "desove": "spawn",
    # asking
    "por que": "why",
    "que": "what",
    "como": "how",
    "donde": "where",
    "cuando": "when",
    "cual": "which",
    "cuantos": "how many",
    "cuantas": "how many",
    "mejor": "best",
    "facil": "easy",
    "principiante": "beginner",
    "principiantes": "beginner",
    "nino": "kid",
    "ninos": "kids",
    "comen": "eat",
    "come": "eat",
    "comer": "eat",
    "pican": "bite",
    "pica": "bite",
    "picar": "bite",
    "necesito": "need",
    "usar": "use",
    "uso": "use",
    "para": "for",
    "en": "in",
    "con": "with",
    # states whose Spanish name differs
    "tejas": "texas",
    "nuevo mexico": "new mexico",
    "carolina del norte": "north carolina",
    "carolina del sur": "south carolina",
    "dakota del norte": "north dakota",
    "dakota del sur": "south dakota",
    "nueva york": "new york",
    "nueva jersey": "new jersey",
    "pensilvania": "pennsylvania",
    "luisiana": "louisiana",
    "misisipi": "mississippi",
    "misuri": "missouri",
    "virginia occidental": "west virginia",
}

# Words a Spanish question has and an English one doesn't.
_SPANISH_WORDS = frozenset(
    "que como donde cuando cual cuales para pescar pesca pesco carnada senuelo anzuelo lombriz lombrices "
    "con el la los las del una uno es en mi por uso usar hay necesito puedo mejor bagre lobina mojarra "
    "trucha licencia lago rio orilla".split()
)
_SPANISH_CHARS = re.compile(r"[ñ¿¡]|[áéíóú]")
_WORD_RE = re.compile(r"[a-z0-9']+")


def fold(text: str) -> str:
    """Lowercased, accents off: "Cómo" and "como" are one word here."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def is_spanish(text: str) -> bool:
    if not text or has_chinese(text):
        return False
    if _SPANISH_CHARS.search(text.lower()):
        return True
    return len(set(_WORD_RE.findall(fold(text))) & _SPANISH_WORDS) >= 2


_PHRASES = sorted(GLOSSARY.items(), key=lambda kv: -len(kv[0]))
_PATTERNS = [(re.compile(rf"(?<![a-z]){re.escape(es)}(?![a-z])"), en) for es, en in _PHRASES]


def to_english(text: str) -> str:
    """The question in the words the guides use. A word the glossary doesn't
    have is left as it is: fish names English and Spanish share ("crappie"),
    numbers, a state's name."""
    out = re.sub(r"[¿¡?!.,;:]", " ", fold(text))
    for pattern, english in _PATTERNS:
        out = pattern.sub(f" {english} ", out)
    return " ".join(out.split())
