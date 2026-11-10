"""Every name a piece of gear goes by, for finding photos of it in open
catalogues by their titles, tags and captions (scan_catalogs.py).

Not only the trade names: the words anglers actually use, regional and
slang names (US South, UK, Australia), brand names used as nouns ("a
Zebco", "a Rapala"), common misspellings, and the names in the languages
Flickr tags are most often written in. Brand names here are search terms
only; the app itself names no brands.

Each item has two lists:
  strong  names that mean the item on their own ("crankbait", "bobber");
  weak    names that also mean something else ("spoon", "cricket",
          "float", "worm") and count only when a fishing word is in the
          same record (CONTEXT, below).
GROUP_TERMS are names for a kind of gear without saying which item
("fishing reel", "lure", "sinker"): a photo found by them is gear of that
group, item unknown, which is still useful (the training labels groups).

Matching is on lower-cased text with punctuation turned into spaces, on
whole words; Flickr tags are also matched with their spaces taken out
("fishingreel", "spinnerbait"), see scan_catalogs.matcher().
"""

ITEMS: dict[str, dict[str, list[str]]] = {
    # ---- rods -----------------------------------------------------------
    "rod-spinning": {
        "strong": ["spinning rod", "spinning rods", "spinning pole", "spin rod", "spinning outfit",
                   "spinning combo", "spinning rod and reel", "ultralight rod", "ultra light rod",
                   "ultra-light rod", "ul rod", "light action rod", "medium action rod",
                   "spinning stick", "drop shot rod", "finesse rod",
                   # other languages
                   "spinnrute", "spinnangel", "canne à lancer", "canne lancer", "caña spinning",
                   "caña de spinning", "canna da spinning", "spinhengel", "haspelspö", "spinnestang",
                   "спиннинг", "スピニングロッド", "纺车竿", "直柄竿", "스피닝대"],
        "weak": [],
    },
    "rod-baitcasting": {
        "strong": ["casting rod", "casting rods", "baitcasting rod", "baitcaster rod", "bait casting rod",
                   "baitcast rod", "casting pole", "flipping stick", "flippin stick", "flipping rod",
                   "pitching rod", "musky rod", "muskie rod", "trigger grip rod", "pistol grip rod",
                   "casting outfit", "baitcasting combo", "baitcaster combo",
                   "boat rod", "trolling rod", "surf rod", "surf casting rod", "surfcasting rod",
                   "beachcaster", "beach caster", "pier rod", "conventional rod", "overhead rod",
                   "boat pole", "jigging rod", "popping rod", "stand up rod",
                   "baitcasterrute", "casting rute", "canne casting", "caña casting", "canna da casting",
                   "castingspö", "ベイトロッド", "枪柄竿", "水滴竿", "베이트대"],
        "weak": [],
    },
    "rod-fly": {
        "strong": ["fly rod", "fly rods", "flyrod", "flyrods", "fly-rod", "fly fishing rod", "flyfishing rod",
                   "fly pole", "fly rod and reel", "fly outfit", "fly reel", "fly reels", "flyreel",
                   "switch rod", "spey rod", "two handed rod", "double handed rod", "split cane rod",
                   "split cane", "bamboo fly rod", "fly combo", "fly fishing reel", "fly line reel",
                   "fliegenrute", "fliegenrolle", "canne à mouche", "moulinet mouche", "caña de mosca",
                   "carrete de mosca", "canna da mosca", "vliegenhengel", "flugspö", "fluestang",
                   "perhovapa", "нахлыст", "フライロッド", "フライリール", "飞钓竿", "飞钓轮", "플라이대"],
        "weak": [],
    },
    "rod-ice": {
        "strong": ["ice rod", "ice rods", "ice fishing rod", "ice fishing rods", "ice pole", "ice fishing pole",
                   "ice jigging rod", "jigging stick", "ice combo", "ice fishing combo", "tip up", "tip-up",
                   "tipup", "tip ups", "tip-ups", "tipups", "tilt", "tilts", "jaw jacker", "deadstick",
                   "dead stick", "ice fishing tip up", "pilkerute", "eisangel", "isfiskespö", "pimpelspö",
                   "talvionki", "pilkkivapa", "зимняя удочка", "冰钓竿", "얼음낚싯대"],
        "weak": [],
    },
    "pole-cane": {
        "strong": ["cane pole", "cane poles", "bamboo pole", "bamboo fishing pole", "bamboo rod",
                   "bamboo fishing rod", "cane fishing pole", "crappie pole", "bream buster",
                   "brim buster", "jig pole", "dipping pole", "dabbing pole", "willow pole",
                   "tenkara", "tenkara rod", "fixed line rod", "fixed-line rod", "telescopic pole",
                   "roach pole", "match pole", "whip pole", "kids cane pole", "pole and line",
                   "stippruten", "stipprute", "canne à coup", "canna fissa", "vaste hengel",
                   "metespö", "onki", "удочка", "延べ竿", "のべ竿", "竹竿", "台钓竿", "手竿", "민낚싯대"],
        "weak": ["whip", "pole"],
    },
    "combo-spincast": {
        "strong": ["spincast", "spin cast", "spin-cast", "spincaster", "spincast reel", "spin cast reel",
                   "spincast combo", "spincast rod", "push button reel", "push-button reel",
                   "pushbutton reel", "closed face reel", "closed-face reel", "closed faced reel",
                   "closed reel", "zebco", "zebco 33", "zebco 202", "kids fishing pole", "kid's fishing pole",
                   "kids fishing rod", "kid's fishing rod", "youth fishing rod", "youth rod",
                   "children's fishing rod", "child's fishing pole", "beginner fishing rod",
                   "rod and reel combo", "rod reel combo", "fishing combo", "starter rod",
                   "geschlossene rolle", "kapselrolle", "moulinet fermé", "carrete cerrado",
                   "mulinello chiuso", "spincastrulle", "儿童鱼竿"],
        "weak": ["combo"],
    },
    # ---- reels ----------------------------------------------------------
    "reel-spinning": {
        "strong": ["spinning reel", "spinning reels", "spin reel", "open face reel", "open-face reel",
                   "open faced reel", "openface reel", "fixed spool reel", "fixed-spool reel",
                   "fixed spool", "threadline", "threadline reel", "eggbeater", "egg beater reel",
                   "coffee grinder reel", "front drag reel", "rear drag reel", "ultralight reel",
                   "ultra light reel", "spinning wheel reel", "bail arm", "bail wire",
                   "stationärrolle", "stationaerrolle", "moulinet spinning", "moulinet à tambour fixe",
                   "carrete spinning", "carrete de spinning", "mulinello spinning", "mulinello a bobina fissa",
                   "werpmolen", "spinmolen", "haspelrulle", "haspelsnelle", "avokela", "kołowrotek",
                   "molinete", "безынерционная катушка", "スピニングリール", "纺车轮", "纺车渔轮",
                   "스피닝릴"],
        "weak": [],
    },
    "reel-baitcasting": {
        "strong": ["baitcasting reel", "baitcasting reels", "baitcaster", "baitcasters", "bait caster",
                   "baitcast reel", "bait-cast reel", "bait casting reel", "casting reel", "casting reels",
                   "low profile reel", "low-profile reel", "lowprofile reel", "round reel", "round baitcaster",
                   "round baitcasting reel", "level wind reel", "level-wind reel", "levelwind",
                   "levelwind reel", "conventional reel", "conventional reels", "overhead reel",
                   "overhead reels", "multiplier reel", "multiplier", "multiplying reel", "star drag reel",
                   "lever drag reel", "trolling reel", "line counter reel", "linecounter reel",
                   "big game reel", "ambassadeur", "abu ambassadeur",
                   "baitcastrolle", "multirolle", "moulinet casting", "moulinet tournant",
                   "carrete de casting", "carrete baitcasting", "mulinello rotante", "mulinello da casting",
                   "multiplicator", "multimolen", "multirulle", "carretilha",
                   "мультипликаторная катушка", "мультипликатор", "ベイトリール", "両軸リール",
                   "水滴轮", "鼓轮", "베이트릴", "장구통릴"],
        "weak": [],
    },
    # ---- line -----------------------------------------------------------
    "line-mono": {
        "strong": ["monofilament", "monofilament line", "mono line", "mono fishing line", "nylon line",
                   "nylon fishing line", "fluorocarbon", "fluorocarbon line", "fluoro line", "fluoro leader",
                   "copolymer line", "tippet", "tippet spool", "leader material", "spool of line",
                   "line spool", "spool of fishing line", "fishing line spool",
                   "monofile", "monofilschnur", "nylonschnur", "fil nylon", "nylon de pêche", "monofilo",
                   "sedal", "hilo de pescar", "nylon", "monofilament lijn", "nylonlina", "siima",
                   "żyłka", "леска", "ナイロンライン", "フロロカーボン", "道糸", "尼龙线", "碳线", "鱼线",
                   "나일론줄", "카본줄", "낚싯줄"],
        "weak": ["mono", "fluoro", "line"],
    },
    "line-braid": {
        "strong": ["braided line", "braided fishing line", "braid line", "braided", "superline", "super line",
                   "spectra line", "dyneema line", "pe line", "dacron backing", "backing line",
                   "fly line", "fly lines", "flyline", "geflochtene schnur", "geflecht", "tresse",
                   "fil tressé", "trenzado", "línea trenzada", "trecciato", "gevlochten lijn",
                   "flätlina", "kuitusiima", "plecionka", "плетёнка", "плетенка", "peライン", "pe线",
                   "大力马", "합사"],
        "weak": ["braid", "backing"],
    },
    # ---- hooks ----------------------------------------------------------
    "hook-j": {
        "strong": ["j hook", "j-hook", "j hooks", "j-hooks", "baitholder hook", "bait holder hook",
                   "baitholder hooks", "aberdeen hook", "aberdeen hooks", "octopus hook", "octopus hooks",
                   "worm hook", "worm hooks", "offset hook", "offset worm hook", "ewg hook", "wide gap hook",
                   "extra wide gap", "kahle hook", "kahle hooks", "single hook", "long shank hook",
                   "short shank hook", "snelled hook", "snelled hooks", "egg hook", "live bait hook",
                   "o'shaughnessy hook", "sproat hook", "limerick hook", "beak hook", "siwash hook",
                   "drop shot hook", "weedless hook", "barbless hook", "barbed hook", "fly hook",
                   "einzelhaken", "hameçon simple", "anzuelo simple", "amo singolo", "enkele haak",
                   "enkelkrok", "одинарный крючок", "シングルフック", "单钩", "伊势尼", "袖钩"],
        "weak": ["single"],
    },
    "hook-circle": {
        "strong": ["circle hook", "circle hooks", "circle-hook", "circlehook", "inline circle hook",
                   "non-offset circle hook", "non offset circle hook", "kahle circle",
                   "circle-haken", "kreishaken", "hameçon circle", "anzuelo circular", "amo circle",
                   "cirkelkrok", "サークルフック", "圆钩"],
        "weak": [],
    },
    "hook-treble": {
        "strong": ["treble hook", "treble hooks", "treblehook", "triple hook", "triple hooks",
                   "trebles", "treble-hook", "three prong hook", "3 prong hook", "double hook",
                   "double hooks", "drilling", "drillingshaken", "hameçon triple", "anzuelo triple",
                   "ancorina", "dreghaak", "trekrok", "kolmihaara", "kotwiczka", "тройник",
                   "トレブルフック", "三本钩", "锚钩", "트레블훅"],
        "weak": ["treble", "triple"],
    },
    # ---- sinkers --------------------------------------------------------
    "sinker-split-shot": {
        "strong": ["split shot", "split-shot", "splitshot", "split shots", "split shot sinker",
                   "split shot weights", "removable split shot", "bb shot", "dust shot", "shot weights",
                   "lead shot", "shotting", "schrotblei", "bleischrot", "plombs fendus", "plomb fendu",
                   "perdigones", "pallini", "hagel", "hagelblyn", "дробинка", "ガン玉", "咬铅", "조개봉돌"],
        "weak": ["shot"],
    },
    "sinker-egg": {
        "strong": ["egg sinker", "egg sinkers", "egg weight", "egg weights", "sliding sinker", "slip sinker",
                   "slip sinkers", "bullet weight", "bullet weights", "bullet sinker", "worm weight",
                   "worm weights", "tungsten weight", "tungsten weights", "barrel sinker", "barrel sinkers",
                   "olive sinker", "ball sinker", "running ball sinker", "running sinker", "texas rig weight",
                   "durchlaufblei", "olivenblei", "plomb olive", "plomb coulissant", "plomo de corredera",
                   "piombo scorrevole", "glijlood", "glidande sänke", "скользящее грузило",
                   "中通オモリ", "跑铅", "空心铅"],
        "weak": [],
    },
    "sinker-bank": {
        "strong": ["bank sinker", "bank sinkers", "pyramid sinker", "pyramid sinkers", "pyramid weight",
                   "bell sinker", "dipsey sinker", "dipsey", "drop shot weight", "drop-shot weight",
                   "walking sinker", "no-roll sinker", "no roll sinker", "bottom bouncer", "sputnik sinker",
                   "breakaway lead", "grip lead", "watch lead", "torpedo sinker", "trolling sinker",
                   "downrigger weight", "downrigger ball", "cannonball weight", "inline weight",
                   "birnenblei", "krallenblei", "plomb poire", "plomb pyramide", "plomo pera",
                   "piombo a pera", "werplood", "sänke", "søkke", "грузило", "ナス型オモリ",
                   "吊坠", "铅坠", "봉돌"],
        "weak": [],
    },
    # ---- floats ---------------------------------------------------------
    "bobber": {
        "strong": ["bobber", "bobbers", "fishing bobber", "fishing bobbers", "red and white bobber",
                   "round bobber", "clip-on bobber", "clip on bobber", "snap bobber", "dobber", "dobbers",
                   "popping cork", "popping corks", "fishing cork", "cork bobber", "bubble float",
                   "casting bubble", "strike indicator", "strike indicators", "indicator bobber",
                   "spring bobber", "bobber stop", "kugelpose", "bouchon", "boya", "galleggiante sferico",
                   "dobber", "dupp", "flöte", "kork", "koho", "spławik", "поплавок", "玉ウキ", "浮漂",
                   "鱼漂", "浮子", "찌"],
        "weak": ["cork", "corks", "indicator", "bubble"],
    },
    "float-slip": {
        "strong": ["slip bobber", "slip bobbers", "slip float", "slip floats", "slider float", "sliding float",
                   "pencil float", "pencil bobber", "stick float", "stick floats", "waggler", "wagglers",
                   "quill float", "porcupine quill", "porcupine quills", "balsa float", "pole float",
                   "pole floats", "crappie float", "thill float", "avon float", "chubber float",
                   "pellet waggler", "dart float", "drift float", "trotting float", "fishing float",
                   "fishing floats", "angelpose", "laufpose", "pose", "posen", "flotteur", "flotteurs",
                   "flotador", "flotadores", "galleggiante", "galleggianti", "hengeldobber", "glidflöte",
                   "glidedupp", "liukukoho", "棒ウキ", "電気ウキ", "立漂", "夜光漂", "막대찌", "구멍찌"],
        "weak": ["float", "floats", "quill", "quills"],
    },
    # ---- terminal tackle ------------------------------------------------
    "swivel": {
        "strong": ["barrel swivel", "barrel swivels", "snap swivel", "snap swivels", "ball bearing swivel",
                   "crane swivel", "rolling swivel", "three way swivel", "three-way swivel", "3-way swivel",
                   "3 way swivel", "duolock snap", "duo lock snap", "coastlock snap", "fastlock snap",
                   "fishing snap", "fishing snaps", "split ring", "split rings", "solid ring",
                   "wirbel", "karabinerwirbel", "émerillon", "emerillon", "agrafe", "emerillón",
                   "girella", "girelle", "wartel", "lekkerwartel", "lekker", "svivel", "lekkari",
                   "krętlik", "вертлюг", "застежка", "サルカン", "スナップ", "八字环", "转环",
                   "别针", "도래", "스냅도래"],
        "weak": ["swivel", "swivels", "snap", "snaps"],
    },
    "leader-wire": {
        "strong": ["wire leader", "wire leaders", "steel leader", "steel leaders", "wire trace", "steel trace",
                   "trace wire", "titanium leader", "bite wire", "pike leader", "pike trace",
                   "leader wire", "shock leader", "stahlvorfach", "titanvorfach", "vorfach", "bas de ligne",
                   "bas de ligne acier", "cable acero", "líder de acero", "cavetto in acciaio",
                   "staalonderlijn", "stålperuk", "ståltafs", "teräsperuke", "przypon", "поводок",
                   "ワイヤーリーダー", "钢丝前导", "前导线", "子线", "목줄"],
        "weak": ["leader", "leaders", "trace"],
    },
    # ---- lures ----------------------------------------------------------
    "jig-head": {
        "strong": ["jig head", "jig heads", "jighead", "jigheads", "jig-head", "ball head jig", "ballhead jig",
                   "round head jig", "darter head", "darter jig", "shaky head", "shakey head", "ned rig",
                   "ned head", "crappie jig", "crappie jigs", "marabou jig", "marabou jigs", "bucktail jig",
                   "bucktail jigs", "hair jig", "tube jig", "tube jigs", "football jig", "flipping jig",
                   "flippin jig", "swim jig", "swimjig", "arky jig", "casting jig", "jig and pig",
                   "jig n pig", "leadhead", "lead head", "lead head jig", "leadhead jig", "panfish jig",
                   "ice jig", "ice jigs", "tungsten jig", "hair jigs", "skirted jig", "rubber jig",
                   "bladed jig", "chatterbait", "chatter bait", "vibrating jig", "underspin",
                   "jigkopf", "jigköpfe", "bleikopf", "tête plombée", "tete plombee", "cabeza plomada",
                   "testina piombata", "loodkop", "jigghuvud", "jigipää", "główka jigowa",
                   "джиг головка", "джиг-головка", "ジグヘッド", "铅头钩", "铅头", "지그헤드"],
        "weak": ["jig", "jigs", "jigging", "bucktail", "marabou"],
    },
    "lure-soft-worm": {
        "strong": ["plastic worm", "plastic worms", "rubber worm", "rubber worms", "soft plastic worm",
                   "soft plastic worms", "soft worm", "soft worms", "senko", "senkos", "stick worm",
                   "stickworm", "wacky worm", "wacky rig", "wacky rigged", "texas rig", "texas rigged",
                   "texas-rigged", "carolina rig", "carolina rigged", "finesse worm", "ribbon tail worm",
                   "ribbontail", "curly tail worm", "trick worm", "floating worm", "creature bait",
                   "creature baits", "craw bait", "soft plastic", "soft plastics", "soft-plastic",
                   "soft plastic lure", "soft plastic lures", "soft bait", "soft baits", "softbait",
                   "softbaits", "power worm", "powerworm", "gulp worm", "plastic lizard", "soft lizard",
                   "tube bait", "tube baits", "tube lure", "fluke", "flukes", "soft jerkbait",
                   "drop shot worm", "dropshot worm", "ned worm", "stick bait worm", "beaver bait", "soft craw",
                   "gummiwurm", "gummiköder", "kunstwurm", "leurre souple", "leurres souples", "ver souple",
                   "vinilo", "vinilos", "gusano de plástico", "esca siliconica", "artificiale siliconico",
                   "gumbete", "gummibete", "kumikala", "kumi uistin", "guma",
                   "твистер", "силиконовая приманка", "ワーム", "软虫", "软饵", "软假饵", "웜"],
        "weak": ["worm", "worms", "plastics", "lizard", "lizards", "tube", "tubes", "stickbait"],
    },
    "lure-grub": {
        "strong": ["grub lure", "grub tail", "grub tails", "curly tail grub", "curly tail grubs", "curlytail",
                   "curly tail", "curly-tail", "twister tail", "twistertail", "mister twister",
                   "single tail grub", "double tail grub", "twin tail grub", "plastic grub",
                   "plastic grubs", "soft grub", "twister", "twister köder", "twister-köder", "twisters",
                   "grub", "grubs", "カーリーテール", "卷尾蛆", "卷尾"],
        "weak": [],
    },
    "lure-swimbait": {
        "strong": ["swimbait", "swimbaits", "swim bait", "swim baits", "swim-bait", "paddle tail",
                   "paddletail", "paddle-tail", "paddle tails", "shad tail", "shadtail", "shad body",
                   "soft shad", "soft shads", "boot tail", "boottail", "glide bait", "glidebait",
                   "glide baits", "line thru swimbait", "line-thru", "jointed swimbait", "hard swimbait",
                   "umbrella rig", "alabama rig", "a-rig", "kopyto", "ripper", "rippers",
                   "gummifisch", "gummifische", "shad souple", "swim shad", "vinilo shad",
                   "シャッドテール", "スイムベイト", "T尾", "鱼形软饵", "섀드웜"],
        "weak": ["shads", "paddle"],
    },
    "lure-crankbait": {
        "strong": ["crankbait", "crankbaits", "crank bait", "crank baits", "crank-bait", "squarebill",
                   "square bill", "square-bill", "squarebills", "deep diver", "deep divers",
                   "deep diving crankbait", "diving plug", "diving plugs", "diving lure", "diving lures",
                   "floating minnow", "floating minnows", "minnow lure", "minnow lures", "minnow plug",
                   "rapala", "rapalas", "shad rap", "fat rap", "hot n tot", "hot'n tot", "flatfish lure",
                   "wiggle wart", "hardbait", "hardbaits", "hard bait", "hard baits", "hard lure",
                   "hard lures", "hard body lure", "hardbody", "lipped lure", "lipped crankbait",
                   "bill lure", "balsa lure", "balsa crankbait", "wooden lure", "wooden lures",
                   "wooden plug", "fishing plug", "fishing plugs", "trolling plug", "trolling lure",
                   "wobbler", "wobblers", "wobbler köder", "poisson nageur", "poissons nageurs",
                   "leurre dur", "pez artificial", "señuelo duro", "artificiale duro", "plug", "pluggen",
                   "vaappu", "vaapu", "vaaput", "woblery", "woblerek", "воблер", "воблеры",
                   "クランクベイト", "ミノー", "ハードルアー", "米诺", "硬饵", "胖子", "크랭크베이트", "미노우"],
        "weak": ["crank", "cranks", "plug", "plugs", "minnow"],
    },
    "lure-lipless": {
        "strong": ["lipless crankbait", "lipless crankbaits", "lipless crank", "lipless", "rattle trap",
                   "rattletrap", "rattletraps", "rat-l-trap", "rat l trap", "ratl trap", "rattlebait",
                   "rattle bait", "vibration lure", "vibration bait", "vib lure", "vibe lure", "blade bait",
                   "blade baits", "silver buddy", "sonar lure", "cicada lure", "lipless lure",
                   "vibrationsköder", "leurre vibrant", "lame vibrante", "señuelo vibrante",
                   "バイブレーション", "VIB", "铅笔", "바이브레이션"],
        "weak": ["trap", "traps"],
    },
    "lure-jerkbait": {
        "strong": ["jerkbait", "jerkbaits", "jerk bait", "jerk baits", "jerk-bait", "twitch bait",
                   "twitchbait", "suspending jerkbait", "suspending minnow", "husky jerk", "x-rap",
                   "smithwick rogue", "slashbait", "slash bait", "jointed minnow", "jointed minnows",
                   "jointed lure", "jointed plug", "glider lure", "pike jerkbait", "musky jerkbait",
                   "jerkbait hecht", "jerk", "jerks", "jerkbait suspending", "ジャークベイト",
                   "サスペンドミノー", "悬浮米诺", "저크베이트"],
        "weak": ["stickbait", "stick bait", "jerks"],
    },
    "lure-popper": {
        "strong": ["popper", "poppers", "popping plug", "popping plugs", "popper lure", "chugger", "chuggers",
                   "topwater", "top water", "top-water", "topwater lure", "topwater lures", "topwater plug",
                   "surface lure", "surface lures", "surface plug", "surface plugs", "walking bait",
                   "walk the dog", "walk-the-dog", "zara spook", "spook lure", "pencil popper",
                   "pencil bait", "prop bait", "propbait", "prop baits", "whopper plopper", "plopper",
                   "buzzbait", "buzz bait", "buzzbaits", "frog lure", "frog lures", "hollow body frog",
                   "hollow-body frog", "topwater frog", "rubber frog lure", "jitterbug", "hula popper",
                   "crawler bait", "wake bait", "wakebait", "torpedo lure", "devil's horse",
                   "oberflächenköder", "leurre de surface", "señuelo de superficie", "artificiale di superficie",
                   "pinta-uistin", "поппер", "ポッパー", "ペンシルベイト", "トップウォーター",
                   "波爬", "铅笔饵", "雷蛙", "水面系", "포퍼", "탑워터"],
        "weak": ["frog", "frogs", "spook"],
    },
    "lure-spinnerbait": {
        "strong": ["spinnerbait", "spinnerbaits", "spinner bait", "spinner baits", "spinner-bait",
                   "safety pin lure", "safety-pin lure", "beetle spin", "beetlespin", "beetle spins",
                   "tandem spinner", "colorado blade", "willow blade", "willowleaf blade", "indiana blade",
                   "double willow", "blade lure", "bladed lure", "buzz bait", "in-line buzzbait",
                   "spinnerbait hecht", "spinner-bait", "スピナーベイト", "复合亮片", "스피너베이트"],
        "weak": ["blade", "blades"],
    },
    "lure-inline-spinner": {
        "strong": ["inline spinner", "inline spinners", "in-line spinner", "in-line spinners",
                   "in line spinner", "mepps", "mepps spinner", "rooster tail", "roostertail",
                   "rooster tails", "panther martin", "blue fox spinner", "vibrax", "aglia", "comet spinner",
                   "french spinner", "bucktail spinner", "trout spinner", "spinner lure", "spinner lures",
                   "fishing spinner", "fishing spinners", "spinner fly", "worm harness", "crawler harness",
                   "spinner rig", "spinner harness", "dodger", "flasher", "cowbell", "lake troll",
                   "spinnerköder", "cuillère tournante", "cuilliere tournante", "cucharilla giratoria",
                   "cucchiaino rotante", "spinners", "spinnare", "lippa", "obrotówka", "вертушка",
                   "вращающаяся блесна", "スピナー", "旋转亮片", "亮片", "스피너"],
        "weak": ["spinner"],
    },
    "lure-spoon": {
        "strong": ["fishing spoon", "fishing spoons", "spoon lure", "spoon lures", "casting spoon",
                   "casting spoons", "jigging spoon", "jigging spoons", "trolling spoon", "trolling spoons",
                   "weedless spoon", "flutter spoon", "spoonbait", "spoon bait", "spoonbaits", "daredevle",
                   "dardevle", "daredevil spoon", "kastmaster", "little cleo", "johnson silver minnow",
                   "krocodile spoon", "wobbling spoon", "wobbler spoon", "metal spoon lure", "metal jig",
                   "metal jigs", "metal lure", "metal lures", "slab spoon", "slab", "slabs", "sabiki",
                   "diamond jig", "hopkins spoon", "blinker", "blinkers", "löffelköder", "cuillère ondulante",
                   "cuiller ondulante", "cucharilla ondulante", "cucharilla", "cucchiaino ondulante",
                   "cucchiaino", "lepel", "kunstaas lepel", "skeddrag", "sluk", "drag", "lusikka",
                   "lusikkauistin", "błystka", "błystki", "колебалка", "блесна", "блесны", "スプーン",
                   "メタルジグ", "勺子", "铁板", "汤匙亮片", "亮片勺", "스푼", "메탈지그"],
        "weak": ["spoon", "spoons"],
    },
    # ---- flies ----------------------------------------------------------
    "fly-dry": {
        "strong": ["dry fly", "dry flies", "dryfly", "fishing fly", "fishing flies", "trout fly", "trout flies",
                   "salmon fly pattern", "fly tying", "fly-tying", "flytying", "fly tyer", "fly tier",
                   "tied flies", "tied fly", "wet fly", "wet flies", "nymph fly", "nymphs fly",
                   "streamer fly", "streamer flies", "woolly bugger", "wooly bugger", "wooly booger",
                   "elk hair caddis", "parachute adams", "adams dry fly", "royal coachman",
                   "pheasant tail nymph", "hare's ear nymph", "zebra midge", "mayfly pattern",
                   "fly pattern", "fly patterns", "fly box", "flybox", "fly boxes", "bass bug", "bass bugs",
                   "popper fly", "deer hair bug", "salmon fly", "steelhead fly", "tube fly", "san juan worm",
                   "egg pattern", "streamer pattern", "trockenfliege", "nassfliege", "fliegenbinden",
                   "mouche sèche", "mouche seche", "montage de mouches", "mosca seca", "moscas",
                   "mosca secca", "droge vlieg", "torrfluga", "tørrflue", "perho", "perhot", "sucha mucha",
                   "сухая мушка", "мушка", "ドライフライ", "毛鉤", "毛ばり", "飞钓毛钩", "毛钩", "드라이플라이"],
        "weak": ["fly", "flies", "nymph", "nymphs", "streamer", "streamers", "midge", "emerger", "hackle",
                 "caddis", "mayfly"],
    },
    # ---- bait -----------------------------------------------------------
    "bait-nightcrawler": {
        "strong": ["nightcrawler", "nightcrawlers", "night crawler", "night crawlers", "nite crawler",
                   "nite crawlers", "red wiggler", "red wigglers", "redworm", "redworms", "red worm",
                   "red worms", "dew worm", "dew worms", "dewworm", "lobworm", "lobworms", "lob worm",
                   "angleworm", "angleworms", "angle worm", "garden hackle", "fishing worm", "fishing worms",
                   "bait worm", "bait worms", "worm on hook", "worm on a hook", "worms on a hook",
                   "live worm", "live worms", "worm bait", "bloodworm", "bloodworms", "sandworm",
                   "sandworms", "ragworm", "ragworms", "lugworm", "lugworms", "dendrobaena",
                   "canadian nightcrawler", "european nightcrawler", "wiggler", "wigglers",
                   "tauwurm", "tauwürmer", "rotwurm", "mistwurm", "wattwurm", "ver de terre", "vers de terre",
                   "lombric", "gros ver", "lombriz", "lombrices", "gusanos", "lombrico", "lombrichi",
                   "dauwworm", "pier", "pieren", "daggmask", "metemask", "meitemark", "kastemato",
                   "onkimato", "dżdżownica", "червь", "червяк", "выползок", "ミミズ", "みみず", "蚯蚓",
                   "红虫", "地龙", "지렁이"],
        "weak": ["worm", "worms", "earthworm", "earthworms", "crawler", "crawlers"],
    },
    "bait-minnow": {
        "strong": ["bait fish", "baitfish", "bait minnow", "bait minnows", "live minnow", "live minnows",
                   "golden shiner", "golden shiners", "fathead minnow", "fathead minnows", "bait shiner",
                   "bait shiners", "live shiner", "live shiners", "creek chub bait", "mud minnow",
                   "mudminnow", "killifish", "mummichog", "deadbait", "dead bait", "deadbaits", "livebait",
                   "live baitfish", "bait herring", "bait sardine", "pilchard", "pilchards",
                   "menhaden", "pogie", "pogies", "pinfish", "ballyhoo", "bait mullet", "finger mullet",
                   "threadfin shad", "gizzard shad", "bait shad", "köderfisch", "köderfische", "vif",
                   "mud minnows",
                   "poisson vif", "pez cebo", "carnada viva", "esca viva", "pesciolino", "aasvis",
                   "levend aas", "betesfisk", "agnfisk", "syöttikala", "żywiec", "живец", "活き餌", "活饵",
                   "小鱼饵", "생미끼"],
        "weak": ["minnow", "minnows", "shiner", "shiners", "shad", "herring", "sardine", "sardines",
                 "mullet", "chub", "chubs", "sucker", "suckers", "dace", "goby", "gobies", "bunker"],
    },
    "bait-crayfish": {
        "strong": ["crayfish", "crawfish", "crawdad", "crawdads", "crawdaddy", "mudbug", "mudbugs", "yabby",
                   "yabbies", "yabbie", "craw dad", "crayfish bait", "crawfish bait",
                   "flusskrebs", "krebs", "écrevisse", "ecrevisse", "écrevisses", "cangrejo de río",
                   "gambero di fiume", "rivierkreeft", "kräfta", "kreps", "rapu", "rak", "раки", "рак",
                   "ザリガニ", "小龙虾", "螯虾", "가재"],
        "weak": ["craw", "craws", "crayfishes"],
    },
    "bait-waxworm": {
        "strong": ["waxworm", "waxworms", "wax worm", "wax worms", "waxie", "waxies", "mealworm", "mealworms",
                   "meal worm", "meal worms", "eurolarvae", "euro larvae", "mousie", "mousies", "rat tail maggot",
                   "spikes and mousies", "bait maggots", "fishing maggots", "goldenrod grub", "goldenrod grubs",
                   "superworm", "superworms", "butterworm", "butterworms", "bee moth larvae", "bait grubs",
                   "fishing grubs", "maden", "made", "bienenmade", "mehlwurm", "asticot", "asticots",
                   "teigne", "ver de farine", "gusano de la miel", "gusano de harina", "bigattini",
                   "bigattino", "camola del miele", "made", "maden", "fly larvae", "fluglarver", "toukka",
                   "toukat", "białe robaki", "опарыш", "мотыль", "サシ", "ブドウ虫", "蛆", "面包虫",
                   "大麦虫", "구더기"],
        "weak": ["maggot", "maggots", "spike", "spikes", "pinkies", "casters", "grub", "grubs", "larvae",
                 "silkworm", "silkworms"],
    },
    "bait-cricket": {
        "strong": ["cricket bait", "bait crickets", "live crickets", "cricket tube", "cricket box",
                   "cricket cage", "fishing crickets", "grasshopper bait", "hopper bait",
                   "heuschrecke köder", "grillon appât", "grillo cebo", "コオロギ餌", "蟋蟀饵"],
        "weak": ["cricket", "crickets", "grasshopper", "grasshoppers", "hopper", "hoppers", "katydid",
                 "katydids"],
    },
    "bait-leech": {
        "strong": ["ribbon leech", "ribbon leeches", "bait leech", "bait leeches", "leech bait", "live leeches",
                   "fishing leeches", "blutegel köder", "sangsue", "sanguijuela", "sanguisuga", "bloedzuiger",
                   "blodigel", "iilimato", "pijawka", "пиявка", "蚂蟥", "水蛭"],
        "weak": ["leech", "leeches"],
    },
    "bait-shrimp": {
        "strong": ["grass shrimp", "ghost shrimp", "mud shrimp", "live shrimp", "bait shrimp", "frozen shrimp bait",
                   "shrimp bait", "bait prawn", "bait prawns", "sand flea", "sand fleas", "sand crab",
                   "sand crabs", "mole crab", "mole crabs", "peeler crab", "peeler crabs", "soft crab",
                   "fiddler crab bait", "bait squid", "squid bait", "clam bait", "mussel bait", "krill bait",
                   "garnelen köder", "crevette appât", "camarón vivo", "carnada de camarón", "gamberetto esca",
                   "garnaal aas", "räka bete", "katkarapu", "креветка", "エビ餌", "虾饵", "새우미끼"],
        "weak": ["shrimp", "prawn", "prawns", "squid", "clam", "clams", "krill", "mussel", "mussels"],
    },
    "bait-cut": {
        "strong": ["cut bait", "cutbait", "cut baits", "chunk bait", "chunk baits", "strip bait", "bait strip",
                   "bait strips", "fish chunks", "bunker chunk", "bunker chunks", "mackerel strip",
                   "squid strip", "shad chunk", "skipjack strip", "fetzenköder", "fischfetzen",
                   "morceau de poisson", "trozo de pescado", "trancio esca", "vissnipper", "fiskbit",
                   "切り身", "鱼块饵"],
        "weak": ["mackerel", "chunks", "strips"],
    },
    "bait-liver": {
        "strong": ["chicken liver", "chicken livers", "liver bait", "stink bait", "stinkbait", "stink baits",
                   "punch bait", "dip bait", "dipbait", "blood bait", "catfish bait", "catfish baits",
                   "cheese bait", "dough bait", "doughbait", "dough ball", "doughballs", "dough balls",
                   "bread ball", "bread balls", "bread bait", "bread flake", "hot dog bait",
                   "hühnerleber", "foie de volaille appât", "hígado de pollo", "fegato di pollo", "kippenlever",
                   "鸡肝", "臭饵"],
        "weak": ["liver", "livers", "dough", "bread", "cheese", "hot dog", "hotdog"],
    },
    "bait-roe": {
        "strong": ["salmon eggs", "salmon egg", "trout eggs", "spawn sac", "spawn sacs", "spawn bag",
                   "spawn bags", "egg sac", "egg sacs", "egg loop", "egg cure", "cured eggs", "cured roe",
                   "skein", "skeins", "single eggs", "single egg", "fish egg bait", "roe bait", "bait eggs",
                   "powerbait eggs", "lachseier", "rogen", "œufs de saumon", "oeufs de saumon",
                   "huevas de salmón", "uova di salmone", "zalmeieren", "laxrom", "rogn", "mäti",
                   "ikra", "икра", "イクラ", "筋子", "鱼卵"],
        "weak": ["roe", "eggs", "fish eggs"],
    },
    "bait-corn": {
        "strong": ["corn bait", "bait corn", "sweetcorn bait", "fishing corn", "boilie", "boilies",
                   "pellet bait", "pellet baits", "particle bait", "particle baits", "hemp seed", "hempseed",
                   "tiger nuts", "tigernuts", "powerbait", "power bait", "trout bait", "trout baits",
                   "trout dough", "marshmallow bait", "mais köder", "maïs appât", "bouillettes", "bouillette",
                   "esche granulari", "maïs", "boilies", "majsbete", "ボイリー", "玉米饵", "颗粒饵",
                   "商品饵", "饵料", "떡밥"],
        "weak": ["corn", "sweetcorn", "sweet corn", "kernel corn", "corn kernels", "kernels", "maize", "pellets",
                 "pellet", "marshmallow", "marshmallows"],
    },
    # ---- tools ----------------------------------------------------------
    "tool-tackle-box": {
        "strong": ["tackle box", "tackle boxes", "tacklebox", "tackleboxes", "tackle bag", "tackle bags",
                   "tackle tray", "tackle trays", "tackle storage", "tackle backpack", "tackle organizer",
                   "lure box", "lure boxes", "hook box", "utility box", "plano box", "tackle chest",
                   "tackle drawer", "angelkoffer", "köderbox", "kunstköderbox", "boîte à pêche",
                   "caja de pesca", "cassetta da pesca", "viskoffer", "tacklebox", "betesask", "slukboks",
                   "viehelaatikko", "skrzynka wędkarska", "рыболовный ящик", "タックルボックス",
                   "钓箱", "路亚盒", "饵盒", "태클박스"],
        "weak": ["tackle", "box"],
    },
    "tool-pliers": {
        "strong": ["fishing pliers", "fishing plier", "split ring pliers", "hook remover", "hook removers",
                   "hook disgorger", "disgorger", "disgorgers", "dehooker", "de-hooker", "hook out",
                   "line cutter", "line cutters", "line clipper", "line clippers", "fish gripper",
                   "fish grippers", "fish grip", "lip gripper", "lip grip", "lip grips", "boga grip",
                   "bogagrip", "jaw spreader", "jaw spreaders", "angelzange", "hakenlöser", "lösezange",
                   "pince à pêche", "dégorgeoir", "degorgeoir", "alicate de pesca", "desanzuelador",
                   "pinza da pesca", "slamatore", "onthaker", "peang", "fisketang", "kalastajan pihdit",
                   "szczypce wędkarskie", "экстрактор", "フィッシュグリップ", "プライヤー", "路亚钳",
                   "控鱼器", "取钩器", "摘钩器", "피쉬그립"],
        "weak": ["pliers", "forceps", "hemostat", "hemostats", "nippers", "clippers"],
    },
    "tool-net": {
        "strong": ["landing net", "landing nets", "dip net", "dip nets", "dipnet", "dipnets", "scoop net",
                   "scoop nets", "keep net", "keepnet", "keepnets", "trout net", "rubber net", "rubber mesh net",
                   "boat net", "salmon net", "net man", "cast net", "castnet", "throw net",
                   "kescher", "unterfangkescher", "setzkescher", "épuisette", "epuisette", "bourriche",
                   "salabre", "sacadera", "copo", "guadino", "nassa", "schepnet", "leefnet", "håv",
                   "haavi", "podbierak", "подсак", "садок", "タモ網", "玉網", "抄网", "鱼护", "뜰채"],
        "weak": ["net", "nets", "fishing net", "fish net"],
    },
    "tool-stringer": {
        "strong": ["fish stringer", "stringer of fish", "chain stringer", "rope stringer", "stringers of fish",
                   "creel", "creels", "wicker creel", "fish creel", "fishing creel", "fish basket",
                   "fishing basket", "kukan", "fischkorb", "panier de pêche", "cesta de pesca", "cestino",
                   "fiskekorg", "kalakori", "кукан", "ビク", "鱼篓", "살림망"],
        "weak": ["stringer", "stringers"],
    },
    "tool-bucket": {
        "strong": ["bait bucket", "bait buckets", "minnow bucket", "minnow buckets", "minnow trap",
                   "minnow traps", "bait well", "baitwell", "livewell", "live well", "bait cooler",
                   "worm bucket", "bait can", "bait box", "bait boxes", "bait container", "bait cup",
                   "worm box", "worm can", "bait tray", "köderdose", "köfi eimer", "seau à vifs",
                   "boîte à appâts", "cubo de cebo", "secchio esca", "aasemmer", "betesburk",
                   "syöttiämpäri", "バッカン", "活饵桶", "饵料盒", "미끼통"],
        "weak": ["bucket", "buckets"],
    },
    "tool-lifejacket": {
        "strong": ["life jacket", "life jackets", "lifejacket", "lifejackets", "life vest", "life vests",
                   "lifevest", "pfd", "personal flotation device", "personal flotation devices",
                   "life preserver", "buoyancy aid", "buoyancy vest", "float coat", "floatation vest",
                   "flotation vest", "inflatable life vest", "inflatable pfd", "fishing vest pfd",
                   "rettungsweste", "schwimmweste", "gilet de sauvetage", "chaleco salvavidas",
                   "giubbotto salvagente", "reddingsvest", "flytväst", "redningsvest", "pelastusliivi",
                   "kamizelka ratunkowa", "спасательный жилет", "ライフジャケット", "救生衣", "구명조끼"],
        "weak": [],
    },
    "tool-measure": {
        "strong": ["measuring board", "measuring boards", "bump board", "bumpboard", "fish ruler", "fish rulers",
                   "fish measure", "fish measuring", "fish scale", "fish scales", "hand scale", "spring scale",
                   "boga scale", "lip grip scale", "catch measure", "measure board", "fish tape",
                   "messbrett", "fischwaage", "maßband fisch", "règle à poisson", "peson", "regla de pesca",
                   "báscula de pesca", "metro pesca", "meetlat", "mätbräda", "mittalauta",
                   "メジャー", "スケール", "量鱼尺", "鱼秤", "계측자"],
        "weak": ["ruler", "scale", "scales", "tape measure"],
    },
    "tool-sunglasses": {
        "strong": ["polarized sunglasses", "polarised sunglasses", "polarized glasses", "polarised glasses",
                   "polarized lenses", "polarised lenses", "polaroids", "polarizing sunglasses",
                   "fishing sunglasses", "fishing glasses", "polbrille", "polarisationsbrille",
                   "lunettes polarisantes", "gafas polarizadas", "occhiali polarizzati", "polariserende bril",
                   "polariserade solglasögon", "polaroidlasit", "偏光グラス", "偏光镜", "편광안경"],
        "weak": ["sunglasses", "shades"],
    },
    "tool-ice-auger": {
        "strong": ["ice auger", "ice augers", "hand auger", "power auger", "gas auger", "electric auger",
                   "ice drill", "ice drills", "ice spud", "spud bar", "ice chisel", "ice skimmer",
                   "ice scoop", "ice fishing auger", "eisbohrer", "tarière à glace", "barrena de hielo",
                   "trivella da ghiaccio", "ijsboor", "isborr", "isbor", "kaira", "jääkaira", "świder",
                   "ледобур", "アイスオーガー", "冰钻", "얼음끌"],
        "weak": ["auger", "augers", "spud"],
    },
}

# A kind of gear, not which item. Strong: say gear on their own; weak: need
# a fishing word nearby.
GROUP_TERMS: dict[str, dict[str, list[str]]] = {
    "rod": {
        "strong": ["fishing rod", "fishing rods", "fishing pole", "fishing poles", "fishin pole", "fishin' pole",
                   "fishing stick", "fishingrod", "fishingrods", "fishingpole", "fishingpoles", "rod and reel",
                   "rod & reel", "rods and reels", "angling rod", "angle rod", "telescopic rod",
                   "telescopic fishing rod", "travel rod", "pack rod", "carp rod", "feeder rod", "match rod",
                   "coarse rod", "pike rod", "trout rod", "bass rod", "salmon rod", "rod rack",
                   "rod holder", "rod holders", "angelrute", "angelruten", "rute", "canne à pêche",
                   "canne a peche", "cannes à pêche", "caña de pescar", "cañas de pescar", "caña de pesca",
                   "canna da pesca", "canne da pesca", "hengel", "hengels", "fiskespö", "metspö",
                   "fiskestang", "fiskestenger", "kalastusvapa", "vapa", "wędka", "wędki", "vara de pesca",
                   "varas de pesca", "удочка", "удилище", "釣竿", "釣り竿", "ロッド", "鱼竿", "钓竿", "渔竿",
                   "路亚竿", "海竿", "矶竿", "낚싯대", "낚시대"],
        "weak": ["rod", "rods", "pole", "poles", "stick"],
    },
    "reel": {
        "strong": ["fishing reel", "fishing reels", "fishingreel", "fishingreels", "centrepin", "centerpin",
                   "centrepin reel", "centerpin reel", "reel seat", "angelrolle", "angelrollen", "rolle",
                   "moulinet", "moulinets", "carrete", "carretes", "mulinello", "mulinelli", "molen",
                   "rulle", "snelle", "kela", "kelat", "kołowrotek", "kołowrotki", "molinete", "carretilha",
                   "катушка", "リール", "渔轮", "鱼线轮", "卷线器", "릴"],
        "weak": ["reel", "reels", "spool"],
    },
    "line": {
        "strong": ["fishing line", "fishing lines", "fishingline", "fishline", "fish line", "line spooler",
                   "angelschnur", "schnur", "fil de pêche", "ligne de pêche", "hilo de pesca", "línea de pesca",
                   "lenza", "filo da pesca", "vislijn", "fiskelina", "fiskesnøre", "kalastussiima",
                   "linha de pesca", "леска", "釣り糸", "ライン", "鱼线", "钓线", "낚싯줄"],
        "weak": [],
    },
    "hook": {
        "strong": ["fish hook", "fish hooks", "fishhook", "fishhooks", "fishing hook", "fishing hooks",
                   "fishinghook", "bait hook", "bait hooks", "hook and line", "hooks and line", "rig",
                   "fishing rig", "terminal tackle", "bottom rig", "high low rig", "hi-lo rig",
                   "fishfinder rig", "drop shot rig", "dropper loop", "snell knot", "palomar knot",
                   "improved clinch knot", "clinch knot", "angelhaken", "haken", "hameçon", "hameçons",
                   "hamecon", "anzuelo", "anzuelos", "amo", "ami", "vishaak", "haak", "haakjes", "fiskekrok",
                   "krok", "kroker", "koukku", "koukut", "haczyk", "haczyki", "anzol", "anzóis", "крючок",
                   "крючки", "釣り針", "釣針", "針", "フック", "鱼钩", "钓钩", "鱼钩子", "낚싯바늘", "바늘"],
        "weak": ["hook", "hooks", "rigs"],
    },
    "sinker": {
        "strong": ["sinker", "sinkers", "fishing weight", "fishing weights", "lead weight", "lead weights",
                   "fishing sinker", "fishing sinkers", "ledger weight", "leger weight", "ledger", "leger",
                   "plummet", "plumb weight", "angelblei", "blei", "bleie", "plomb", "plombs", "plomo",
                   "plomos", "piombo", "piombi", "lood", "loodjes", "sänken", "søkker", "paino", "painot",
                   "ciężarek", "ciężarki", "chumbada", "chumbo", "грузило", "грузила", "オモリ", "錘",
                   "铅坠", "铅", "봉돌"],
        "weak": ["weight", "weights", "lead"],
    },
    "float": {
        "strong": ["fishing float", "fishing floats", "fishing bobber", "fishing bobbers", "angelpose",
                   "ウキ", "浮き", "浮标", "浮漂", "찌"],
        "weak": [],
    },
    "lure": {
        "strong": ["fishing lure", "fishing lures", "fishinglure", "fishinglures", "lure", "lures",
                   "artificial lure", "artificial lures", "artificial bait", "artificial baits", "fake bait",
                   "bass lure", "bass lures", "trout lure", "trout lures", "pike lure", "pike lures",
                   "musky lure", "muskie lure", "musky lures", "salmon lure", "walleye lure", "crappie lure",
                   "saltwater lure", "lure collection", "antique lure", "antique lures", "vintage lure",
                   "vintage lures", "old lures", "homemade lure", "handmade lure", "lure making",
                   "lure painting", "kunstköder", "köder", "leurre", "leurres", "señuelo", "señuelos",
                   "senuelo", "esca artificiale", "artificiale", "artificiali", "kunstaas", "fiskedrag",
                   "drag", "agn", "viehe", "vieheet", "uistin", "uistimet", "przynęta", "przynęty",
                   "isca artificial", "iscas artificiais", "приманка", "приманки", "ルアー", "疑似餌",
                   "路亚", "路亚饵", "假饵", "拟饵", "루어"],
        "weak": ["bait", "baits", "tackle"],
    },
    "bait": {
        "strong": ["fishing bait", "fishing baits", "fishingbait", "live bait", "natural bait", "köder", "naturköder",
                   "appât", "appâts", "appat", "cebo", "cebos", "carnada", "esca", "esche", "aas", "bete",
                   "agn", "syötti", "syötit", "zanęta", "isca", "iscas", "наживка", "насадка", "приманка",
                   "餌", "エサ", "えさ", "鱼饵", "钓饵", "饵", "미끼"],
        "weak": ["bait", "baits"],
    },
    # Some gear, which not said (like Open Images' Tackle should have been).
    "gear": {
        "strong": ["fishing tackle", "fishing gear", "fishing equipment", "angling equipment", "angling gear",
                   "fishing kit", "fishing supplies", "angelzubehör",
                   "angelausrüstung", "angelgeräte", "matériel de pêche", "material de pesca",
                   "attrezzatura da pesca", "hengelsportartikelen", "fiskeutrustning", "fiskeutstyr",
                   "kalastusvälineet", "sprzęt wędkarski", "рыболовные снасти", "снасти", "釣具", "釣り具",
                   "渔具", "钓具", "鱼具", "낚시용품", "낚시장비"],
        "weak": ["tackle", "gear"],
    },
}

# Words that make a weak name count: the record is about fishing.
CONTEXT = [
    # Words about the act of fishing only. Not "fish" (fish and chips, fish
    # bowl), not fish species (Pike County, Cape Cod, salmon on a plate),
    # not "rod", "reel", "hook", "catch" (curtain rod hooks, film reel). A
    # weak name counts only within five words of one of these (Matcher).
    "fishing", "fished", "fisherman", "fishermen", "fishin", "angler", "anglers", "angling", "tackle",
    "bait", "baits", "lure", "lures", "fly fishing", "flyfishing", "fly-fishing", "ice fishing", "icefishing",
    "tacklebox", "tackle box", "fishingtrip", "fishing trip", "gone fishing", "fliegenfischen",
    "angeln", "angler", "angelsport", "pêche", "peche", "pêcheur", "pesca", "pescar", "pescador", "pescatore",
    "vissen", "visser", "hengelen", "fiske", "fiska", "fisket", "kalastus", "kalastaja", "wędkarstwo",
    "wędkowanie", "рыбалка", "рыболов", "釣り", "釣", "钓鱼", "钓", "路亚", "낚시",
]

# Records about these are fishing but not gear; they don't stop a match,
# they flag it for the spot check.
NOT_GEAR_HINTS = [
    "fishing boat", "fishing boats", "fishing village", "fishing harbour", "fishing harbor", "fishing port",
    "fishing fleet", "trawler", "trawlers", "fish market", "fishmarket", "fishing net", "fishing nets",
    "lobster pot", "lobster pots", "crab pot", "crab pots", "fish farm", "aquarium", "sushi", "seafood",
    "fish and chips", "restaurant", "fishing pier", "fishing lake", "fishing trip", "sunset",
    "bait shop", "bait and tackle", "bait & tackle", "bait store", "baitshop", "tackle shop", "tackle store",
    "crawfish boil", "crayfish boil", "fly fishing", "flyfishing", "ice fishing",
]

# Names above that also mean something everyday outside fishing, in English
# or in the language they come from (a kitchen spoon, a fidget spinner, a
# Dutch "pier", food, music): moved to the weak list wherever they are, so
# they count only next to a fishing word.
AMBIGUOUS = {
    # other languages' words that are ordinary words elsewhere
    "drag", "agn", "aas", "bete", "esca", "esche", "amo", "ami", "haak", "haakjes", "krok", "kroker", "haken",
    "針", "바늘", "フック", "rig", "rak", "kreps", "krebs", "рак", "раки", "vif", "copo", "nassa", "rute",
    "rolle", "molen", "rulle", "snelle", "kela", "kelat", "carrete", "carretes", "moulinet", "moulinets",
    "molinete", "катушка", "릴", "blei", "bleie", "plomb", "plombs", "plomo", "plomos", "piombo", "piombi",
    "lood", "loodjes", "chumbo", "paino", "painot", "ciężarek", "ciężarki", "錘", "铅", "ledger", "leger",
    "plummet", "plumb weight", "tresse", "braided", "nylon", "flöte", "kork", "bouchon", "boya", "koho",
    "flotteur", "flotteurs", "flotador", "flotadores", "galleggiante", "galleggianti", "pose", "posen",
    "wirbel", "agrafe", "スナップ", "drilling", "trebles", "twister", "twisters", "grub", "grubs", "ripper",
    "rippers", "kopyto", "guma", "wobbler", "wobblers", "VIB", "dodger", "flasher", "spinners", "亮片",
    "вертушка", "slab", "slabs", "sluk", "lepel", "cucharilla", "cucchiaino", "lusikka", "勺子", "铁板",
    "スプーン", "스푼", "blinker", "blinkers", "moscas", "perho", "perhot", "мушка", "salmon fly",
    "egg pattern", "fly pattern", "fly patterns", "lombriz", "lombrices", "gusanos", "lombrico", "lombrichi",
    "червь", "червяк", "蚯蚓", "地龙", "지렁이", "ver de terre", "vers de terre", "lombric", "daggmask",
    "meitemark", "kastemato", "dżdżownica", "ミミズ", "みみず", "pesciolino", "pilchard", "pilchards",
    "menhaden", "pinfish", "ballyhoo", "killifish", "mummichog", "golden shiner", "golden shiners",
    "fathead minnow", "fathead minnows", "mud minnow", "mud minnows", "mudminnow", "threadfin shad",
    "gizzard shad", "pogie", "pogies", "finger mullet", "crayfish", "crawfish", "crawdad", "crawdads",
    "crawdaddy", "craw dad", "mudbug", "mudbugs", "yabby", "yabbies", "yabbie", "flusskrebs", "écrevisse",
    "ecrevisse", "écrevisses", "cangrejo de río", "gambero di fiume", "rivierkreeft", "kräfta", "rapu",
    "ザリガニ", "小龙虾", "螯虾", "가재", "mealworm", "mealworms", "meal worm", "meal worms", "superworm",
    "superworms", "butterworm", "butterworms", "maden", "mehlwurm", "bienenmade", "asticot", "asticots",
    "teigne", "ver de farine", "gusano de la miel", "gusano de harina", "camola del miele", "fly larvae",
    "fluglarver", "toukka", "toukat", "białe robaki", "サシ", "ブドウ虫", "蛆", "面包虫", "大麦虫", "구더기",
    "sangsue", "sanguijuela", "sanguisuga", "bloedzuiger", "blodigel", "iilimato", "pijawka", "пиявка", "蚂蟥",
    "水蛭", "sand flea", "sand fleas", "sand crab", "sand crabs", "mole crab", "mole crabs", "katkarapu",
    "креветка", "fish chunks", "dough ball", "doughballs", "dough balls", "bread ball", "bread balls",
    "bread flake", "hühnerleber", "hígado de pollo", "fegato di pollo", "kippenlever", "鸡肝", "salmon eggs",
    "salmon egg", "trout eggs", "skein", "skeins", "single eggs", "single egg", "egg sac", "egg sacs",
    "lachseier", "rogen", "œufs de saumon", "oeufs de saumon", "huevas de salmón", "uova di salmone",
    "zalmeieren", "laxrom", "rogn", "mäti", "ikra", "икра", "イクラ", "筋子", "鱼卵", "hemp seed", "hempseed",
    "tiger nuts", "tigernuts", "maïs", "utility box", "line cutter", "line cutters", "line clipper",
    "line clippers", "peang", "hook out", "プライヤー", "boat net", "salmon net", "cast net", "castnet",
    "throw net", "creel", "creels", "fish basket", "cestino", "fish scale", "fish scales", "hand scale",
    "spring scale", "peson", "メジャー", "スケール", "polaroids", "hand auger", "power auger", "gas auger",
    "electric auger", "ice drill", "ice drills", "ice skimmer", "ice scoop", "świder", "kaira", "rod holder",
    "rod holders", "rod rack", "schnur", "ライン", "haczyk", "haczyki", "koukku", "koukut", "крючок", "крючки",
    "lure", "lures", "köder", "leurre", "leurres", "señuelo", "señuelos", "senuelo", "artificiale",
    "artificiali", "przynęta", "przynęty", "приманка", "приманки", "appât", "appâts", "appat", "cebo", "cebos",
    "carnada", "isca", "iscas", "syötti", "syötit", "насадка", "餌", "エサ", "えさ", "饵", "wiggler",
    "wigglers", "trace wire", "pike leader",
}

AMBIGUOUS |= {"pfd", "fluke", "flukes", "fish scale", "fish scales", "popper", "poppers", "live well",
              "plastic lizard", "hagel", "line spool", "spool of line", "rods"}

# Found by looking at 299 sampled photos (spot_check.py): everyday phrases,
# a dance, a motorcycle style, a French "ambassadeur", microscope "red
# worms", Chinese cricket cages, Native American quillwork.
AMBIGUOUS |= {
    "top water", "walk the dog", "walk-the-dog", "a rig", "a-rig", "deep diver", "deep divers", "red worm",
    "red worms", "cricket cage", "cricket box", "porcupine quill", "porcupine quills", "j hook", "j-hook",
    "j hooks", "j-hooks", "lead shot", "dust shot", "tungsten weight", "tungsten weights", "inline weight",
    "cannonball weight", "split ring", "split rings", "solid ring", "worm box", "worm can", "bait can",
    "scoop net", "spud bar", "measure board", "round reel", "fixed spool", "bail wire", "switch rod",
    "split cane", "bamboo rod", "bamboo pole", "willow pole", "telescopic pole", "ice pole", "tip up",
    "stand up rod", "youth rod", "starter rod", "fishing stick", "angle rod", "travel rod", "pack rod",
    "match rod", "lead weight", "lead weights", "lead head", "paddle tail", "boot tail", "line-thru",
    "curly tail", "willow blade", "double willow", "bill lure", "crawler bait", "soft plastic", "soft plastics",
    "soft-plastic", "pe line", "super line", "backing line", "chicken liver", "chicken livers", "grass shrimp",
    "ghost shrimp", "mud shrimp", "live shrimp", "fishing float", "fishing floats", "nylon line",
    "bucket", "buckets", "life preserver", "float coat", "salmon fly",
}
# Insects and party streamers before they are flies: only "dry fly", "fly tying", "trout flies"...
DROP_EXTRA = {"ambassadeur", "shotting", "jaw jacker", "fly", "flies", "nymph", "nymphs", "streamer",
              "streamers", "midge", "emerger", "hackle", "caddis", "mayfly"}

# A single word counts on its own only when it means fishing gear and
# nothing else; every other single word ("multiplier", "eggbeater",
# "lipless", "jitterbug", "chugger", "rattletrap", "vinilo", "bobber" the
# motorcycle style) needs a fishing word next to it.
SAFE_SINGLE = {
    "crankbait", "crankbaits", "spinnerbait", "spinnerbaits", "jerkbait", "jerkbaits", "swimbait", "swimbaits",
    "squarebill", "squarebills", "chatterbait", "buzzbait", "buzzbaits", "jighead", "jigheads", "leadhead",
    "beetlespin", "paddletail", "shadtail", "boottail", "glidebait", "twistertail", "spoonbait", "spoonbaits",
    "softbait", "softbaits", "hardbait", "hardbaits", "propbait", "wakebait", "rattlebait", "stickworm",
    "kastmaster", "daredevle", "dardevle", "mepps", "sabiki", "topwater", "baitcaster", "baitcasters",
    "levelwind", "spincast", "spincaster", "zebco", "flyrod", "flyrods", "flyreel", "nightcrawler",
    "nightcrawlers", "waxworm", "waxworms", "boilie", "boilies", "lugworm", "lugworms", "ragworm",
    "ragworms", "bloodworm", "bloodworms", "deadbait", "deadbaits", "livebait", "baitfish", "waggler",
    "wagglers", "keepnet", "keepnets", "dipnet", "dipnets", "tacklebox", "tackleboxes", "disgorger",
    "disgorgers", "dehooker", "livewell", "baitwell", "bumpboard", "fishhook", "fishhooks", "fishingrod",
    "fishingrods", "fishingpole", "fishingpoles", "fishingreel", "fishingreels", "fishingline", "fishline",
    "fishinglure", "fishinglures", "flytying", "dryfly", "flybox", "lifejacket", "lifejackets", "lifevest",
    "splitshot", "tipup", "tipups", "circlehook", "treblehook", "jigheads", "monofilament", "fluorocarbon",
    "superline", "flyline", "dobber", "dobbers", "crawdad", "crawdads", "nitecrawler", "stinkbait", "dipbait",
    "cutbait", "powerbait", "hempseed", "tigernuts", "baitholder",
    # other languages: words that only mean fishing gear there
    "angelrute", "angelruten", "angelrolle", "angelrollen", "kunstköder", "stationärrolle", "multirolle",
    "spinnrute", "fliegenrute", "fliegenrolle", "angelhaken", "stahlvorfach", "kescher", "tauwurm",
    "tauwürmer", "gummifisch", "gummifische", "kalastusvapa", "uistin", "uistimet", "vieheet", "wędka",
    "wędki", "kołowrotek", "błystka", "błystki", "spławik", "podbierak", "żywiec", "удочка", "удилище",
    "спиннинг", "блесна", "блесны", "воблер", "воблеры", "поплавок", "грузило", "подсак", "опарыш",
    "épuisette", "hameçon", "hameçons", "anzuelo", "anzuelos", "señuelos", "carretilha", "mulinello",
    "fiskespö", "fiskestang", "haspelrulle", "multirulle", "vliegenhengel", "werpmolen", "kunstaas",
}


def _demote_singles(table):
    for t in table.values():
        keep = []
        for w in t["strong"]:
            single = " " not in w and "-" not in w and not any("぀" <= ch <= "힯" for ch in w)
            if single and w.lower() not in SAFE_SINGLE:
                t["weak"].append(w)
            else:
                keep.append(w)
        t["strong"] = keep


# Never searched for: everyday words that swamp the counts even next to a
# fishing word (a first scan found them matching photo "shots", "single"
# tracks, Tilt-O-Whirl rides, fishermen's nets, fish and chips, fish traps).
DROP = {"made", "pier", "pieren", "lekker", "胖子", "铅笔", "fish tape", "net man", "cowbell", "lippa", "stick",
        "jerk", "jerks", "plug", "pluggen", "tilt", "tilts", "shot", "single", "triple", "snap", "snaps", "trap",
        "traps", "mackerel", "drag", "cheese", "bread", "dough", "hot dog", "hotdog", "eggs", "roe", "chunks",
        "strips", "box", "gear", "tackle", "line", "lead", "weight", "weights", "rig", "rigs", "net", "nets",
        "fishing net", "fish net", "scale", "scales", "herring", "sardine", "sardines", "mullet", "chub", "chubs",
        "sucker", "suckers", "dace", "goby", "gobies", "bunker", "shad", "shads", "clam", "clams", "mussel",
        "mussels", "krill", "kernels", "blade", "blades", "paddle", "single egg", "single eggs", "backing",
        "indicator", "bubble", "spike", "spikes", "larvae", "casters", "pinkies"}


def _key(w):
    """"top-water", "Top water" and "top water" are one name."""
    return " ".join(w.lower().replace("-", " ").replace("'", "").split())


def _tidy(table):
    drop = {_key(w) for w in DROP | DROP_EXTRA}
    amb = {_key(w) for w in AMBIGUOUS}
    for t in table.values():
        strong = [w for w in t["strong"] if _key(w) not in drop]
        t["weak"] = [w for w in t["weak"] if _key(w) not in drop] + [w for w in strong if _key(w) in amb]
        t["strong"] = [w for w in strong if _key(w) not in amb]


_tidy(ITEMS)
_tidy(GROUP_TERMS)
_demote_singles(ITEMS)
_demote_singles(GROUP_TERMS)


def all_terms():
    """(term, kind, target, strength) for every name: kind 'item' or 'group'."""
    for item, t in ITEMS.items():
        for s in ("strong", "weak"):
            for term in t[s]:
                yield term, "item", item, s
    for group, t in GROUP_TERMS.items():
        for s in ("strong", "weak"):
            for term in t[s]:
                yield term, "group", group, s
