"""Today's plan in Chinese, Spanish, Korean and Japanese (services/fishing_plan.py).

The plan's sentences are FishEye's own, written in English in
fishing_plan.py. These are the same sentences, translated by hand: a lure's
name as an angler in that language would say it (a crankbait is a 胖子, a
lipless crankbait a VIB in Chinese and a バイブレーション / 바이브레이션 in
Japanese and Korean, a drop shot a ダウンショット; "carnada", "señuelo" and
"acocil" as Mexican and US Spanish say them), the inch and ounce sizes left
as they are because that is how the tackle is sold here.

Keyed by the English. A sentence that changes with the light ("At dawn, …")
is keyed with "{light}" in its place. A sentence missing here stays in
English: tests/test_plan_text.py checks that none does.
"""
from __future__ import annotations

import re

LANGS = ("zh", "es", "ko", "ja")

LIGHT = {
    "zh": {"dawn": "清晨", "dusk": "黄昏"},
    "es": {"dawn": "amanecer", "dusk": "atardecer"},
    "ko": {"dawn": "새벽", "dusk": "해 질 녘"},
    "ja": {"dawn": "明け方", "dusk": "夕暮れ"},
}

# 16-point compass, as NWS gives wind directions, in each language's
# weather-report words (东北偏北, 북북동, 北北東).
DIRECTIONS = {
    "zh": {
        "N": "北", "NNE": "东北偏北", "NE": "东北", "ENE": "东北偏东", "E": "东", "ESE": "东南偏东", "SE": "东南",
        "SSE": "东南偏南", "S": "南", "SSW": "西南偏南", "SW": "西南", "WSW": "西南偏西", "W": "西", "WNW": "西北偏西",
        "NW": "西北", "NNW": "西北偏北",
    },
    "ko": {
        "N": "북", "NNE": "북북동", "NE": "북동", "ENE": "동북동", "E": "동", "ESE": "동남동", "SE": "남동",
        "SSE": "남남동", "S": "남", "SSW": "남남서", "SW": "남서", "WSW": "서남서", "W": "서", "WNW": "서북서",
        "NW": "북서", "NNW": "북북서",
    },
    "ja": {
        "N": "北", "NNE": "北北東", "NE": "北東", "ENE": "東北東", "E": "東", "ESE": "東南東", "SE": "南東",
        "SSE": "南南東", "S": "南", "SSW": "南南西", "SW": "南西", "WSW": "西南西", "W": "西", "WNW": "西北西",
        "NW": "北西", "NNW": "北北西",
    },
    "es": {
        "N": "norte", "NNE": "nornoreste", "NE": "noreste", "ENE": "estenoreste", "E": "este", "ESE": "estesureste",
        "SE": "sureste", "SSE": "sursureste", "S": "sur", "SSW": "sursuroeste", "SW": "suroeste", "WSW": "oestesuroeste",
        "W": "oeste", "WNW": "oestenoroeste", "NW": "noroeste", "NNW": "nornoroeste",
    },
}

# NWS short forecasts, lowercased; the common ones. Others stay English.
FORECASTS = {
    "zh": {
        "sunny": "晴", "mostly sunny": "大部晴", "partly sunny": "晴间多云", "clear": "晴朗", "mostly clear": "大部晴朗",
        "partly cloudy": "局部多云", "mostly cloudy": "大部多云", "cloudy": "多云", "overcast": "阴",
        "patchy fog": "局部有雾", "areas of fog": "部分地区有雾", "fog": "雾", "haze": "霾",
        "slight chance rain showers": "小概率阵雨", "chance rain showers": "可能有阵雨", "rain showers likely": "很可能有阵雨",
        "rain showers": "阵雨", "light rain": "小雨", "rain": "雨", "heavy rain": "大雨", "drizzle": "毛毛雨",
        "slight chance showers and thunderstorms": "小概率雷阵雨", "chance showers and thunderstorms": "可能有雷阵雨",
        "showers and thunderstorms likely": "很可能有雷阵雨", "showers and thunderstorms": "雷阵雨",
        "chance thunderstorms": "可能有雷暴", "thunderstorms": "雷暴", "snow": "雪", "chance snow showers": "可能有阵雪",
    },
    "es": {
        "sunny": "soleado", "mostly sunny": "mayormente soleado", "partly sunny": "parcialmente soleado",
        "clear": "despejado", "mostly clear": "mayormente despejado", "partly cloudy": "parcialmente nublado",
        "mostly cloudy": "mayormente nublado", "cloudy": "nublado", "overcast": "cubierto",
        "patchy fog": "niebla en partes", "areas of fog": "zonas de niebla", "fog": "niebla", "haze": "bruma",
        "slight chance rain showers": "ligera posibilidad de chubascos", "chance rain showers": "posibles chubascos",
        "rain showers likely": "probables chubascos", "rain showers": "chubascos", "light rain": "lluvia ligera",
        "rain": "lluvia", "heavy rain": "lluvia fuerte", "drizzle": "llovizna",
        "slight chance showers and thunderstorms": "ligera posibilidad de chubascos y tormentas",
        "chance showers and thunderstorms": "posibles chubascos y tormentas",
        "showers and thunderstorms likely": "probables chubascos y tormentas",
        "showers and thunderstorms": "chubascos y tormentas", "chance thunderstorms": "posibles tormentas",
        "thunderstorms": "tormentas", "snow": "nieve", "chance snow showers": "posibles nevadas",
    },
    # The Korea Meteorological Administration's sky words.
    "ko": {
        "sunny": "맑음", "mostly sunny": "대체로 맑음", "partly sunny": "구름조금", "clear": "맑음", "mostly clear": "대체로 맑음",
        "partly cloudy": "구름조금", "mostly cloudy": "구름많음", "cloudy": "흐림", "overcast": "흐림",
        "patchy fog": "곳에 따라 안개", "areas of fog": "곳에 따라 안개", "fog": "안개", "haze": "연무",
        "slight chance rain showers": "소나기 가능성 낮음", "chance rain showers": "소나기 가능성",
        "rain showers likely": "소나기 예상", "rain showers": "소나기", "light rain": "약한 비", "rain": "비",
        "heavy rain": "강한 비", "drizzle": "이슬비",
        "slight chance showers and thunderstorms": "소나기·뇌우 가능성 낮음",
        "chance showers and thunderstorms": "소나기·뇌우 가능성", "showers and thunderstorms likely": "소나기·뇌우 예상",
        "showers and thunderstorms": "소나기·뇌우", "chance thunderstorms": "뇌우 가능성", "thunderstorms": "뇌우",
        "snow": "눈", "chance snow showers": "눈 소나기 가능성",
    },
    "ja": {
        "sunny": "晴れ", "mostly sunny": "おおむね晴れ", "partly sunny": "晴れ時々曇り", "clear": "晴れ",
        "mostly clear": "おおむね晴れ", "partly cloudy": "晴れ時々曇り", "mostly cloudy": "曇りがち", "cloudy": "曇り",
        "overcast": "曇り", "patchy fog": "所により霧", "areas of fog": "所により霧", "fog": "霧", "haze": "もや",
        "slight chance rain showers": "にわか雨の可能性は低い", "chance rain showers": "にわか雨の可能性",
        "rain showers likely": "にわか雨の見込み", "rain showers": "にわか雨", "light rain": "小雨", "rain": "雨",
        "heavy rain": "大雨", "drizzle": "霧雨",
        "slight chance showers and thunderstorms": "にわか雨や雷雨の可能性は低い",
        "chance showers and thunderstorms": "にわか雨や雷雨の可能性",
        "showers and thunderstorms likely": "にわか雨や雷雨の見込み", "showers and thunderstorms": "にわか雨と雷雨",
        "chance thunderstorms": "雷雨の可能性", "thunderstorms": "雷雨", "snow": "雪", "chance snow showers": "にわか雪の可能性",
    },
}

# The plan's fixed sentences and templates (fishing_plan.where_to_fish,
# heads_up, _conditions_line). {mph}, {dir}, {shore}, {from_}, {drop},
# {pct}, {temp}, {sky}, {wind} are filled in by the caller.
TEMPLATES = {
    "zh": {
        "start_cover": "从岬角和障碍物开始：码头、倒木、水草边。",
        "windy_shelter_dir": "风最大 {mph} 英里/小时。去背风的{dir}岸，那里水面平静些，还能抛投。",
        "windy_shelter": "风最大 {mph} 英里/小时。找一个背风的湾。",
        "calm": "风很小，哪边岸都差不多。钓阴影和障碍物：码头、倒木、水草边。",
        "into_wind": "钓风吹向的那一侧岸，从岬角和障碍物开始。",
        "downwind": "试试{shore}岸。那时风从{from_}方吹来，把饵鱼推向那边，所以从那一侧的岬角和障碍物开始。",
        "thunder": "预报有雷暴。一听到雷声就离开水边。",
        "too_windy": "风最大 {mph} 英里/小时：难抛投，小船有危险。",
        "front": "锋面过境，未来一天气温会降 {drop}°F。鱼常在锋面来之前进食，所以越早去越好。",
        "rain": "这个时段可能下雨（概率 {pct}%）。",
        "wind_part": "{dir}风 {wind}",
        "wind_part_nodir": "风 {wind}",
        "joiner": "，",
    },
    "es": {
        "start_cover": "Empieza en las puntas y junto al refugio: muelles, árboles caídos, orillas de hierba.",
        "windy_shelter_dir": "Viento de hasta {mph} mph. Pesca en la orilla {dir} protegida, donde el agua está más tranquila y aún puedes lanzar.",
        "windy_shelter": "Viento de hasta {mph} mph. Busca una ensenada protegida del viento.",
        "calm": "Casi no hay viento, así que ninguna orilla destaca. Pesca la sombra y el refugio: muelles, árboles caídos, orillas de hierba.",
        "into_wind": "Pesca la orilla hacia donde sopla el viento, empezando por las puntas y el refugio.",
        "downwind": "Prueba la orilla {shore}. A esa hora el viento viene del {from_} y empuja la carnada hacia ella, así que empieza por las puntas y el refugio de ese lado.",
        "thunder": "Hay tormentas eléctricas en el pronóstico. Sal del agua al primer trueno.",
        "too_windy": "Viento de hasta {mph} mph: difícil para lanzar, y peligroso en una lancha pequeña.",
        "front": "La temperatura baja {drop}°F en el próximo día porque entra un frente. Los peces suelen comer antes, así que mejor ir pronto.",
        "rain": "Probable lluvia en este horario ({pct}% de probabilidad).",
        "wind_part": "viento del {dir} {wind}",
        "wind_part_nodir": "viento {wind}",
        "joiner": ", ",
    },
    # {dir}, {shore} and {from_} are compass words ("북동"): {dir}쪽 물가,
    # never a particle that changes with the word before it.
    "ko": {
        "start_cover": "곶부리와 커버부터 시작하세요. 선착장, 쓰러진 나무, 수초 가장자리 같은 곳이에요.",
        "windy_shelter_dir": "바람이 최대 시속 {mph}마일이에요. 바람을 막아 주는 {dir}쪽 물가로 가세요. 물이 잔잔해서 아직 던질 수 있어요.",
        "windy_shelter": "바람이 최대 시속 {mph}마일이에요. 바람을 피할 수 있는 후미진 곳을 찾으세요.",
        "calm": "바람이 약해서 어느 물가든 비슷해요. 그늘과 커버를 노리세요. 선착장, 쓰러진 나무, 수초 가장자리 같은 곳이에요.",
        "into_wind": "바람을 받는 물가를 노리고, 곶부리와 커버부터 시작하세요.",
        "downwind": "{shore}쪽 물가를 노려 보세요. 그 시간에는 {from_}쪽에서 바람이 불어 베이트피시를 그쪽으로 몰아요. 그쪽의 곶부리와 커버부터 시작하세요.",
        "thunder": "뇌우 예보가 있어요. 천둥소리가 들리면 바로 물가를 떠나세요.",
        "too_windy": "바람이 최대 시속 {mph}마일이에요. 던지기 어렵고, 작은 보트는 위험해요.",
        "front": "전선이 들어와 앞으로 하루 동안 기온이 {drop}°F 떨어져요. 물고기는 전선이 오기 전에 잘 먹으니, 일찍 가는 게 좋아요.",
        "rain": "이 시간대에는 비가 올 수 있어요(강수 확률 {pct}%).",
        "wind_part": "{dir}풍 {wind}",
        "wind_part_nodir": "바람 {wind}",
        "joiner": ", ",
    },
    "ja": {
        "start_cover": "岬やカバーから始めましょう：桟橋、倒木、水草の際。",
        "windy_shelter_dir": "風は最大で時速{mph}マイル。風をよけられる{dir}岸へ。水面が穏やかで、まだ投げられます。",
        "windy_shelter": "風は最大で時速{mph}マイル。風をよけられる入り江を探しましょう。",
        "calm": "風が弱く、どの岸も大差ありません。日陰とカバーを釣りましょう：桟橋、倒木、水草の際。",
        "into_wind": "風が吹き付ける岸を、岬とカバーから釣りましょう。",
        "downwind": "{shore}岸を試してみましょう。その時間は{from_}から風が吹いて小魚をそちらへ寄せるので、その側の岬とカバーから始めます。",
        "thunder": "雷雨の予報です。雷が聞こえたら、すぐに水辺を離れてください。",
        "too_windy": "風は最大で時速{mph}マイル：投げにくく、小さなボートは危険です。",
        "front": "前線の通過で、この先1日で気温が{drop}°F下がります。魚は前線の前によく食うので、早めがおすすめです。",
        "rain": "この時間帯は雨の可能性があります（降水確率{pct}%）。",
        "wind_part": "{dir}の風 {wind}",
        "wind_part_nodir": "風 {wind}",
        "joiner": "、",
    },
}

# Lure and bait names, and why each was picked.
TEXT: dict[str, dict[str, str]] = {
    "zh": {
        # names
        "1½–2½ in minnows": "1½–2½ 英寸的小鱼（米诺）",
        "1½–2½ in minnows (the preferred bait)": "1½–2½ 英寸的小鱼（首选饵）",
        "1–2 oz slabs in chartreuse, chrome or white": "1–2 盎司铁板（荧光黄绿、电镀或白色）",
        "2–3 in curly-tail grubs on a jighead": "铅头钩配 2–3 英寸卷尾软饵",
        "2–4 in live shad or fathead minnows": "2–4 英寸的活鲥鱼或胖头米诺",
        "2–4 in minnows or shad": "2–4 英寸的小鱼或鲥鱼",
        "3–4 in tube on a 1/8–1/4 oz jighead": "1/8–1/4 盎司铅头钩配 3–4 英寸管状软饵",
        "4–6 in straight-tail worms (green pumpkin or watermelon) on a shaky head or drop shot":
            "4–6 英寸直尾软虫（南瓜绿或西瓜色），配摇摆铅头或倒吊钓组",
        "5 in stick-style worms": "5 英寸棒形软虫",
        "6 in pencil poppers (topwater)": "6 英寸铅笔波扒（水面系）",
        "A small piece of worm or nightcrawler, just enough to cover the hook": "一小段蚯蚓，刚好盖住鱼钩",
        "Beetle-spins": "Beetle Spin（带旋转亮片的铅头钩）",
        "Bucktail jigs": "鹿毛铅头钩",
        "Canned or frozen sweet corn": "罐装或冷冻甜玉米",
        "Chicken liver": "鸡肝",
        "Crankbaits and ¼–½ oz lipless crankbaits": "胖子和 ¼–½ 盎司 VIB（无舌胖子）",
        "Crawdad tails": "小龙虾尾",
        "Crayfish": "小龙虾",
        "Crickets": "蟋蟀",
        "Dough baits such as PowerBait, molded to cover the hook": "PowerBait 之类的面饵，捏成团包住鱼钩",
        "Dough balls and oatmeal-based pack baits": "面团和燕麦底的包料饵",
        "Drop-shot finesse worms": "倒吊钓组配细软虫",
        "Fresh cut shad (fresh beats frozen)": "新鲜切块鲥鱼（新鲜的比冷冻的好）",
        "Grubs on 1/8–½ oz jigheads": "1/8–½ 盎司铅头钩配卷尾软饵",
        "Inline spinners": "旋转亮片",
        "Jerkbaits, and topwater lures twitched like an injured fish": "米诺（Jerkbait），以及像受伤小鱼一样抽动的水面系拟饵",
        "Jigs": "铅头钩（Jig）",
        "Large live minnows, goldfish or bullheads": "大的活小鱼、金鱼或小鲶鱼",
        "Large live shiners (8–9 in) under a bobber": "浮漂下挂大活饵鱼（8–9 英寸的 shiner）",
        "Live shad": "活鲥鱼",
        "Live sunfish, such as bluegill (the go-to bait)": "活的太阳鱼，比如蓝鳃（首选饵）",
        "Live threadfin or gizzard shad": "活的线鳍鲥或美洲真鰶",
        "Ned rig (a short soft-plastic stick on a small jighead) bounced along the bottom":
            "Ned 钓组（小铅头钩配短棒形软饵），贴底跳动",
        "Ned rig: a 3–4 in stick worm on a 1/8–1/4 oz mushroom jighead": "Ned 钓组：1/8–1/4 盎司蘑菇头铅头钩配 3–4 英寸棒形软虫",
        "Nightcrawlers": "大蚯蚓",
        "Plastic worms": "软虫",
        "Poppers and other topwaters near downed trees and lily pads": "波扒等水面系拟饵，打倒木和睡莲旁边",
        "Redworms or other earthworms": "红蚯蚓或其他蚯蚓",
        "Shrimp (stays on the hook well)": "虾（挂钩牢）",
        "Slabs and jigging spoons": "铁板和沉底勺",
        "Small black or brown jigs that look like a snail or insect": "像螺或小虫的黑色、棕色小铅头钩",
        "Small crankbaits": "小胖子",
        "Small grubs and jigs fished near the bottom": "贴底钓的小卷尾软饵和小铅头钩",
        "Small inline spinners, 1/16–1/8 oz (olive, brown, black or white)": "1/16–1/8 盎司小旋转亮片（橄榄绿、棕、黑或白）",
        "Small jigging spoons": "小沉底勺",
        "Small jigs and soft-plastic crawfish": "小铅头钩和软胶小龙虾",
        "Small pieces of worm": "小段蚯蚓",
        "Small poppers": "小波扒",
        "Small poppers at dawn or dusk": "清晨或黄昏用小波扒",
        "Small soft-plastic jigs": "小号软胶铅头钩",
        "Small spoons in gold or silver": "金色或银色小勺形亮片",
        "Spinnerbaits": "复合亮片",
        "Spinnerbaits, heavier ones in current": "复合亮片，有水流时用重一点的",
        "Stinkbait": "臭饵",
        "Swimbaits": "仿生软饵（Swimbait）",
        "Tiny jigs, 1/32 oz and smaller (black works well)": "1/32 盎司及更小的微型铅头钩（黑色好用）",
        "Tiny spinners": "微型旋转亮片",
        "Topwater lures": "水面系拟饵",
        "Topwater lures when schools are breaking the surface": "鱼群在水面炸水时用水面系拟饵",
        "Wax worms": "蜡虫",
        "White or chartreuse marabou jigs in low light": "光线暗时用白色或荧光黄绿的马拉布羽毛铅头钩",
        "Worms and nightcrawlers": "蚯蚓和大蚯蚓",
        "¼–1 oz slabs": "¼–1 盎司铁板",
        "½ oz lipless crankbaits": "½ 盎司 VIB（无舌胖子）",
        # why
        "A bit of flash gets noticed in choppy or cloudy water.": "水面起浪或阴天时，一点闪光更容易被鱼发现。",
        "A classic catfish bait. Fish it on the bottom.": "经典的鲶鱼饵，沉底钓。",
        "A dependable all-round striper lure.": "钓条纹鲈很稳的万能拟饵。",
        "A flashing spinner stands out in choppy or cloudy water.": "起浪或阴天的水里，闪光的亮片很显眼。",
        "A flathead eats only live fish. Fish a live sunfish tight to heavy wood cover.":
            "扁头鲶只吃活鱼。把活太阳鱼贴着大块木头障碍物放。",
        "A front is on the way, and bass often feed hard before it. Cover water fast.":
            "锋面要来了，黑鲈常在锋面前猛吃。快速搜索水域。",
        "A good search bait for finding active fish.": "找活跃鱼的好搜索饵。",
        "A little flash helps in choppy or cloudy water. Retrieve slowly.": "起浪或阴天时，一点闪光有帮助。慢收。",
        "A minnow under a bobber near cover. Crappie's favorite meal.": "在障碍物旁边浮漂下挂小鱼，莓鲈最爱吃的。",
        "A popular, simple way to fish a river pool.": "钓河里深潭常用又简单的方法。",
        "A small bait for a small mouth; fish it near the bottom.": "小嘴配小饵，靠近水底钓。",
        "A small piece of worm on a small hook works for trout.": "小钩挂一小段蚯蚓就能钓鳟鱼。",
        "A small spoon catches stocked trout too.": "小勺形亮片也能钓到放流的鳟鱼。",
        "An easy all-round choice. Cast and retrieve steadily.": "简单的万能选择。抛出去，匀速收线。",
        "At {light} crappie rise to feed. A small popper can draw strikes on top.":
            "{light}莓鲈会上浮觅食，小波扒能引来水面攻击。",
        "At {light}, schools chase shad to the surface. Watch for splashes and cast into them.":
            "{light}，鱼群会把鲥鱼追到水面。看到水花就往里抛。",
        "At {light}, smallmouth hunt the shallows: twitch a surface lure over rock.":
            "{light}，小口黑鲈在浅水捕食：在石头上方抽动水面拟饵。",
        "At {light}, work a popper along shady banks, downed trees and lily pads.":
            "{light}，沿着阴凉的岸边、倒木和睡莲操作波扒。",
        "Bigger live bait tends to catch bigger flatheads.": "活饵越大，钓到的扁头鲶往往越大。",
        "Blue catfish are caught on bait. No lure needed.": "蓝鲶靠饵料钓，不用拟饵。",
        "Blue cats hunt by smell. Fresh cut shad on the bottom is the standard.": "蓝鲶靠嗅觉找食。沉底放新鲜切块鲥鱼是标准做法。",
        "Bluegill feed at the surface at {light}. A small popper is fun and effective.":
            "{light}蓝鳃会在水面吃东西，小波扒又好玩又管用。",
        "Bright sun pushes bass tight to cover. Pitch a jig right into it.": "阳光强时黑鲈会紧贴障碍物。把铅头钩直接投进去。",
        "Bright sun pushes crappie into shade. Drop a small jig next to docks and brush.":
            "阳光强时莓鲈躲进阴影里。在码头和树枝堆旁边放小铅头钩。",
        "Bright sun sends hybrids deeper. Fish a slab straight down.": "阳光强时杂交鲈会下沉。把铁板垂直放下去钓。",
        "Calm, bright water makes bass cautious. Crawl a worm slowly through cover.":
            "无风又明亮时黑鲈很警惕。让软虫在障碍物里慢慢爬。",
        "Carp find a scented bait on the bottom; mold it to hide the hook.": "鲤鱼会找到水底有气味的饵；把饵捏紧盖住鱼钩。",
        "Carp rarely strike lures. Fish bait on the bottom.": "鲤鱼很少咬拟饵。沉底钓饵料。",
        "Cast and retrieve slowly along the bank.": "沿着岸边抛投，慢慢收线。",
        "Casting in wind tears soft baits off. Shrimp stays on the hook.": "有风时抛投容易把软饵甩掉，虾挂得住。",
        "Catfish are caught on bait. No lure needed.": "鲶鱼靠饵料钓，不用拟饵。",
        "Catfish are still feeding after the night. Fish a nightcrawler on the bottom.": "鲶鱼夜里吃完早上还在吃。沉底钓大蚯蚓。",
        "Chum a few handfuls of corn, then fish corn on the bottom over it.": "先撒几把玉米打窝，再在窝上沉底钓玉米。",
        "Clear, bright conditions. A small finesse worm near rock gets bit when bigger baits don't.":
            "天晴水清。大饵没口时，在石头旁用小细软虫能有口。",
        "Clear, bright water: smallmouth see well, so a small, slow finesse bait near rock gets bit.":
            "水清光亮：小口黑鲈看得清楚，所以在石头旁慢慢拖小号细饵才有口。",
        "Clouds and rain put catfish on the move, and a strong-smelling bait helps them find it.":
            "阴天下雨时鲶鱼会四处游动，气味重的饵更容易被找到。",
        "Cover water fast along the windblown side, where shad gather.": "沿着迎风一侧快速搜索，鲥鱼聚在那里。",
        "Covers water fast to find a school.": "能快速搜索水域找鱼群。",
        "Covers water quickly to find a school.": "能很快搜遍水域找到鱼群。",
        "Covers water to find a school.": "搜索水域找鱼群。",
        "Drag it slowly over rock, pausing a few seconds.": "在石头上慢慢拖，停几秒再动。",
        "Drift live shad where you find fish. The most reliable way to catch stripers.":
            "在有鱼的地方漂活鲥鱼，这是钓条纹鲈最稳的办法。",
        "Drum feed on the bottom. Work it slowly near current breaks.": "鼓鱼在水底觅食。在水流变化处慢慢操作。",
        "Drum root along the bottom for crayfish.": "鼓鱼贴着水底翻找小龙虾。",
        "Easy and reliable: cast, let it sink, retrieve steadily.": "简单可靠：抛出、等它下沉、匀速收。",
        "Fish it next to cover. Bass take a real shiner faster than any plastic.": "放在障碍物旁边。黑鲈吃真饵鱼比吃任何软饵都快。",
        "Fish it on or just off the bottom, a little deeper than the bluegill beds.": "贴底或离底一点钓，比蓝鳃的产卵窝稍深一些。",
        "Fish it on the bottom and wait for steady pressure: trout often nibble first.":
            "沉底钓，等竿梢持续往下压再提：鳟鱼常先轻啄几下。",
        "Fish it slowly near brush piles, docks and bridge pilings.": "在树枝堆、码头和桥墩附近慢慢钓。",
        "Fish it slowly near weeds and docks.": "在水草和码头附近慢慢钓。",
        "Fish it where you find a school, under a bobber or on a light weight.": "找到鱼群就在那里钓，用浮漂或轻铅坠。",
        "Flatheads consistently take only live bait. No lure needed.": "扁头鲶基本只吃活饵，不用拟饵。",
        "Flatheads move shallow to feed at {light} and after dark. Put a live sunfish next to wood cover.":
            "{light}和天黑后扁头鲶会游到浅水觅食。把活太阳鱼放在木头障碍物旁边。",
        "For a bigger fish, fish a live shad near drop-offs.": "想钓大鱼，就在落差附近钓活鲥鱼。",
        "Guadalupe bass feed heavily on crawfish.": "瓜达卢佩鲈大量吃小龙虾。",
        "Hybrids rarely pass up live shad or minnows.": "杂交鲈很少放过活鲥鱼或小鱼。",
        "In bright midday sun the schools drop deeper. Jig a slab near the bottom.": "正午阳光强时鱼群会下沉。在水底附近抽动铁板。",
        "In bright sun stripers go deeper. Jig a heavy slab under the schools.": "阳光强时条纹鲈会下沉。在鱼群下方抽动重铁板。",
        "Jig it straight down over brush.": "在树枝堆上方垂直上下抽动。",
        "Jig it under schools of bait.": "在饵鱼群下方抽动。",
        "Let it fall slowly along drop-offs.": "沿着落差让它慢慢下沉。",
        "Low light at {light}. A white or chartreuse jig shows up well.": "{light}光线暗，白色或荧光黄绿的铅头钩很显眼。",
        "Low light at {light}: bass come up and hit surface lures.": "{light}光线暗：黑鲈会上浮攻击水面拟饵。",
        "On bright days bluegill hang in shade by docks and brush. Fish a cricket under a bobber there.":
            "大晴天蓝鳃躲在码头和树枝堆的阴影里。在那里用浮漂挂蟋蟀钓。",
        "On hot, sunny days Guadalupe bass go deeper. Fish a finesse worm slowly near rock.":
            "又热又晴的天，瓜达卢佩鲈会下沉。在石头旁慢慢钓细软虫。",
        "Rain or wind muddies the water: a spinnerbait's flash and vibration are easier to find.":
            "下雨或刮风会把水弄浑：复合亮片的闪光和震动更容易被鱼找到。",
        "Redear feed on snails on the bottom. Fish it slowly there.": "红耳太阳鱼在水底吃螺。在那里慢慢钓。",
        "Retrieve slowly along the bank.": "沿着岸边慢慢收线。",
        "Run it along the windblown bank to cover water quickly.": "沿着迎风岸收线，迅速搜索水域。",
        "Spotted bass favor small soft plastics. Drag it slowly near rock.": "斑点黑鲈偏爱小软饵。在石头旁慢慢拖。",
        "Stripers push bait to the surface at {light}. A big popper draws explosive strikes.":
            "{light}条纹鲈会把饵鱼赶到水面，大波扒能引来爆炸般的攻击。",
        "The classic smallmouth bait: let it sink, then hop it over rocky points.": "钓小口黑鲈的经典饵：让它下沉，再在石头岬角上跳动。",
        "The easiest bite in the lake. Fish it under a bobber near the bank.": "湖里最容易上鱼的饵。在岸边用浮漂钓。",
        "Their favorite food: fish it along the bottom near rock.": "它们最爱吃的：在石头附近贴底钓。",
        "When bass won't chase, a live shiner drifting past cover is hard for them to refuse.":
            "黑鲈不追饵时，从障碍物旁漂过的活饵鱼，它也很难忍住不吃。",
        "Wind chop and cloud cover hide your line, and bass chase a moving, flashing bait.":
            "风浪和云层能遮住你的线，黑鲈会追会动、会闪光的饵。",
        "Wind pushes shad onto the windblown bank and white bass follow. Retrieve steadily along it.":
            "风把鲥鱼推向迎风岸，白鲈跟着过去。沿着那边匀速收线。",
        "Wind pushes shad onto the windblown bank. Fish cut shad on the bottom there.": "风把鲥鱼推向迎风岸。在那里沉底钓切块鲥鱼。",
        "Wind stirs up bait along the windblown bank. Swim a shad-like bait through it.":
            "风把迎风岸的饵鱼搅起来了。用像鲥鱼的拟饵从那里游过。",
        "With some wind or cloud, swim a stick worm along rocky banks and points.": "有点风或阴天时，沿着石头岸和岬角游动棒形软虫。",
        "Works almost anywhere catfish live.": "有鲶鱼的地方几乎都管用。",
        "Works in almost any conditions. Fish it slowly near cover.": "几乎什么天气都管用。在障碍物附近慢慢钓。",
        "Worms catch more drum than any other bait. Fish them on the bottom.": "蚯蚓钓鼓鱼比什么饵都多。沉底钓。",
        "A standard choice for this fish.": "这种鱼的常用选择。",
        "A standard bait for this fish.": "这种鱼的常用饵。",
    },
    "es": {
        # names
        "1½–2½ in minnows": "Pececillos de 1½–2½ pulgadas",
        "1½–2½ in minnows (the preferred bait)": "Pececillos de 1½–2½ pulgadas (la carnada preferida)",
        "1–2 oz slabs in chartreuse, chrome or white": "Slabs de 1–2 oz en chartreuse, cromo o blanco",
        "2–3 in curly-tail grubs on a jighead": "Grubs de cola rizada de 2–3 pulgadas en cabeza plomada",
        "2–4 in live shad or fathead minnows": "Sardinas vivas o pececillos cabezones (fathead) de 2–4 pulgadas",
        "2–4 in minnows or shad": "Pececillos o sardinas de 2–4 pulgadas",
        "3–4 in tube on a 1/8–1/4 oz jighead": "Tubo de 3–4 pulgadas en cabeza plomada de 1/8–1/4 oz",
        "4–6 in straight-tail worms (green pumpkin or watermelon) on a shaky head or drop shot":
            "Gusanos de cola recta de 4–6 pulgadas (verde calabaza o sandía) en shaky head o drop shot",
        "5 in stick-style worms": "Gusanos tipo stick de 5 pulgadas",
        "6 in pencil poppers (topwater)": "Poppers tipo lápiz de 6 pulgadas (de superficie)",
        "A small piece of worm or nightcrawler, just enough to cover the hook": "Un pedacito de lombriz, lo justo para cubrir el anzuelo",
        "Beetle-spins": "Beetle-spins (jig con cucharilla)",
        "Bucktail jigs": "Jigs de pelo de venado (bucktail)",
        "Canned or frozen sweet corn": "Elote dulce de lata o congelado",
        "Chicken liver": "Hígado de pollo",
        "Crankbaits and ¼–½ oz lipless crankbaits": "Crankbaits y crankbaits sin paleta de ¼–½ oz",
        "Crawdad tails": "Colas de acocil",
        "Crayfish": "Acociles",
        "Crickets": "Grillos",
        "Dough baits such as PowerBait, molded to cover the hook": "Masas como PowerBait, moldeadas para cubrir el anzuelo",
        "Dough balls and oatmeal-based pack baits": "Bolitas de masa y engodos a base de avena",
        "Drop-shot finesse worms": "Gusanos finesse en drop shot",
        "Fresh cut shad (fresh beats frozen)": "Sardina fresca en trozos (la fresca gana a la congelada)",
        "Grubs on 1/8–½ oz jigheads": "Grubs en cabezas plomadas de 1/8–½ oz",
        "Inline spinners": "Cucharillas giratorias",
        "Jerkbaits, and topwater lures twitched like an injured fish": "Jerkbaits, y señuelos de superficie movidos a tirones como un pez herido",
        "Jigs": "Jigs",
        "Large live minnows, goldfish or bullheads": "Pececillos grandes vivos, carpitas doradas o bagrecitos",
        "Large live shiners (8–9 in) under a bobber": "Shiners grandes vivos (8–9 pulgadas) bajo una boya",
        "Live shad": "Sardina viva",
        "Live sunfish, such as bluegill (the go-to bait)": "Mojarras vivas, como la de agallas azules (la carnada de cajón)",
        "Live threadfin or gizzard shad": "Sardina maya o sardina molleja viva",
        "Ned rig (a short soft-plastic stick on a small jighead) bounced along the bottom":
            "Ned rig (un palito corto de plástico suave en una cabeza plomada pequeña) brincando por el fondo",
        "Ned rig: a 3–4 in stick worm on a 1/8–1/4 oz mushroom jighead":
            "Ned rig: un gusano tipo stick de 3–4 pulgadas en una cabeza plomada tipo hongo de 1/8–1/4 oz",
        "Nightcrawlers": "Lombrices grandes",
        "Plastic worms": "Gusanos de plástico",
        "Poppers and other topwaters near downed trees and lily pads": "Poppers y otros señuelos de superficie cerca de árboles caídos y lirios",
        "Redworms or other earthworms": "Lombrices rojas u otras lombrices de tierra",
        "Shrimp (stays on the hook well)": "Camarón (se queda bien en el anzuelo)",
        "Slabs and jigging spoons": "Slabs y cucharas para jiggear",
        "Small black or brown jigs that look like a snail or insect": "Jigs pequeños negros o cafés que parecen un caracol o un insecto",
        "Small crankbaits": "Crankbaits pequeños",
        "Small grubs and jigs fished near the bottom": "Grubs y jigs pequeños pescados cerca del fondo",
        "Small inline spinners, 1/16–1/8 oz (olive, brown, black or white)":
            "Cucharillas giratorias pequeñas de 1/16–1/8 oz (verde olivo, café, negro o blanco)",
        "Small jigging spoons": "Cucharas pequeñas para jiggear",
        "Small jigs and soft-plastic crawfish": "Jigs pequeños y acociles de plástico suave",
        "Small pieces of worm": "Pedacitos de lombriz",
        "Small poppers": "Poppers pequeños",
        "Small poppers at dawn or dusk": "Poppers pequeños al amanecer o al atardecer",
        "Small soft-plastic jigs": "Jigs pequeños de plástico suave",
        "Small spoons in gold or silver": "Cucharas pequeñas doradas o plateadas",
        "Spinnerbaits": "Spinnerbaits",
        "Spinnerbaits, heavier ones in current": "Spinnerbaits, más pesados en corriente",
        "Stinkbait": "Carnada apestosa",
        "Swimbaits": "Swimbaits",
        "Tiny jigs, 1/32 oz and smaller (black works well)": "Jigs diminutos de 1/32 oz o menos (el negro funciona bien)",
        "Tiny spinners": "Cucharillas diminutas",
        "Topwater lures": "Señuelos de superficie",
        "Topwater lures when schools are breaking the surface": "Señuelos de superficie cuando los cardúmenes rompen el agua",
        "Wax worms": "Gusanos de cera",
        "White or chartreuse marabou jigs in low light": "Jigs de marabú blancos o chartreuse con poca luz",
        "Worms and nightcrawlers": "Lombrices",
        "¼–1 oz slabs": "Slabs de ¼–1 oz",
        "½ oz lipless crankbaits": "Crankbaits sin paleta de ½ oz",
        # why
        "A bit of flash gets noticed in choppy or cloudy water.": "Un poco de destello se nota más con agua picada o nublado.",
        "A classic catfish bait. Fish it on the bottom.": "Una carnada clásica para bagre. Péscalo en el fondo.",
        "A dependable all-round striper lure.": "Un señuelo confiable para lobina rayada en casi todo.",
        "A flashing spinner stands out in choppy or cloudy water.": "Una cucharilla que destella resalta con agua picada o nublado.",
        "A flathead eats only live fish. Fish a live sunfish tight to heavy wood cover.":
            "El bagre cabeza plana solo come peces vivos. Pon una mojarra viva pegada a troncos gruesos.",
        "A front is on the way, and bass often feed hard before it. Cover water fast.":
            "Viene un frente, y la lobina suele comer fuerte antes. Recorre agua rápido.",
        "A good search bait for finding active fish.": "Un buen señuelo de búsqueda para encontrar peces activos.",
        "A little flash helps in choppy or cloudy water. Retrieve slowly.": "Un poco de destello ayuda con agua picada o nublado. Recoge despacio.",
        "A minnow under a bobber near cover. Crappie's favorite meal.": "Un pececillo bajo una boya cerca del refugio. La comida favorita del crappie.",
        "A popular, simple way to fish a river pool.": "Una forma popular y sencilla de pescar una poza de río.",
        "A small bait for a small mouth; fish it near the bottom.": "Carnada chica para boca chica; péscala cerca del fondo.",
        "A small piece of worm on a small hook works for trout.": "Un pedacito de lombriz en un anzuelo chico funciona para la trucha.",
        "A small spoon catches stocked trout too.": "Una cuchara pequeña también saca truchas sembradas.",
        "An easy all-round choice. Cast and retrieve steadily.": "Una opción fácil para todo. Lanza y recoge a ritmo parejo.",
        "At {light} crappie rise to feed. A small popper can draw strikes on top.":
            "Al {light} el crappie sube a comer. Un popper pequeño puede provocar ataques arriba.",
        "At {light}, schools chase shad to the surface. Watch for splashes and cast into them.":
            "Al {light}, los cardúmenes persiguen sardinas hasta la superficie. Busca salpicaduras y lanza ahí.",
        "At {light}, smallmouth hunt the shallows: twitch a surface lure over rock.":
            "Al {light}, la lobina de boca chica caza en lo bajito: mueve a tirones un señuelo de superficie sobre las rocas.",
        "At {light}, work a popper along shady banks, downed trees and lily pads.":
            "Al {light}, trabaja un popper por orillas con sombra, árboles caídos y lirios.",
        "Bigger live bait tends to catch bigger flatheads.": "Una carnada viva más grande suele sacar bagres cabeza plana más grandes.",
        "Blue catfish are caught on bait. No lure needed.": "El bagre azul se pesca con carnada. No hace falta señuelo.",
        "Blue cats hunt by smell. Fresh cut shad on the bottom is the standard.":
            "El bagre azul caza por el olfato. Sardina fresca en trozos en el fondo es lo clásico.",
        "Bluegill feed at the surface at {light}. A small popper is fun and effective.":
            "La mojarra come en la superficie al {light}. Un popper pequeño es divertido y funciona.",
        "Bright sun pushes bass tight to cover. Pitch a jig right into it.": "El sol fuerte pega a la lobina al refugio. Mete un jig justo ahí.",
        "Bright sun pushes crappie into shade. Drop a small jig next to docks and brush.":
            "El sol fuerte manda al crappie a la sombra. Baja un jig pequeño junto a muelles y ramas.",
        "Bright sun sends hybrids deeper. Fish a slab straight down.": "El sol fuerte manda a las híbridas más hondo. Pesca un slab derecho hacia abajo.",
        "Calm, bright water makes bass cautious. Crawl a worm slowly through cover.":
            "Con agua calmada y brillante la lobina desconfía. Arrastra un gusano despacio entre el refugio.",
        "Carp find a scented bait on the bottom; mold it to hide the hook.": "La carpa encuentra la carnada con olor en el fondo; moldéala para tapar el anzuelo.",
        "Carp rarely strike lures. Fish bait on the bottom.": "La carpa casi nunca ataca señuelos. Pesca con carnada en el fondo.",
        "Cast and retrieve slowly along the bank.": "Lanza y recoge despacio a lo largo de la orilla.",
        "Casting in wind tears soft baits off. Shrimp stays on the hook.": "Lanzar con viento arranca las carnadas blandas. El camarón se queda en el anzuelo.",
        "Catfish are caught on bait. No lure needed.": "El bagre se pesca con carnada. No hace falta señuelo.",
        "Catfish are still feeding after the night. Fish a nightcrawler on the bottom.":
            "El bagre sigue comiendo después de la noche. Pesca una lombriz grande en el fondo.",
        "Chum a few handfuls of corn, then fish corn on the bottom over it.": "Avienta unos puños de elote como cebo y luego pesca elote en el fondo encima.",
        "Clear, bright conditions. A small finesse worm near rock gets bit when bigger baits don't.":
            "Día claro y brillante. Un gusano finesse chico cerca de las rocas pica cuando los grandes no.",
        "Clear, bright water: smallmouth see well, so a small, slow finesse bait near rock gets bit.":
            "Agua clara y brillante: la lobina de boca chica ve bien, así que un señuelo finesse chico y lento cerca de las rocas pica.",
        "Clouds and rain put catfish on the move, and a strong-smelling bait helps them find it.":
            "Las nubes y la lluvia ponen al bagre en movimiento, y una carnada de olor fuerte le ayuda a encontrarla.",
        "Cover water fast along the windblown side, where shad gather.": "Recorre agua rápido por el lado del viento, donde se juntan las sardinas.",
        "Covers water fast to find a school.": "Recorre agua rápido para encontrar un cardumen.",
        "Covers water quickly to find a school.": "Recorre agua rápido para dar con un cardumen.",
        "Covers water to find a school.": "Recorre agua para encontrar un cardumen.",
        "Drag it slowly over rock, pausing a few seconds.": "Arrástralo despacio sobre las rocas, con pausas de unos segundos.",
        "Drift live shad where you find fish. The most reliable way to catch stripers.":
            "Deja ir sardina viva a la deriva donde encuentres peces. La forma más segura de pescar lobina rayada.",
        "Drum feed on the bottom. Work it slowly near current breaks.": "La corvina come en el fondo. Trabájalo despacio cerca de los cortes de corriente.",
        "Drum root along the bottom for crayfish.": "La corvina hurga en el fondo buscando acociles.",
        "Easy and reliable: cast, let it sink, retrieve steadily.": "Fácil y seguro: lanza, déjalo hundirse y recoge a ritmo parejo.",
        "Fish it next to cover. Bass take a real shiner faster than any plastic.":
            "Péscalo junto al refugio. La lobina toma un shiner de verdad más rápido que cualquier plástico.",
        "Fish it on or just off the bottom, a little deeper than the bluegill beds.":
            "Péscalo en el fondo o apenas arriba, un poco más hondo que los nidos de la mojarra de agallas azules.",
        "Fish it on the bottom and wait for steady pressure: trout often nibble first.":
            "Péscalo en el fondo y espera un jalón firme: la trucha suele picotear primero.",
        "Fish it slowly near brush piles, docks and bridge pilings.": "Péscalo despacio cerca de ramas, muelles y pilotes de puentes.",
        "Fish it slowly near weeds and docks.": "Péscalo despacio cerca de hierbas y muelles.",
        "Fish it where you find a school, under a bobber or on a light weight.": "Péscalo donde encuentres un cardumen, bajo una boya o con un plomo ligero.",
        "Flatheads consistently take only live bait. No lure needed.": "El bagre cabeza plana casi siempre toma solo carnada viva. No hace falta señuelo.",
        "Flatheads move shallow to feed at {light} and after dark. Put a live sunfish next to wood cover.":
            "El bagre cabeza plana sube a lo bajito a comer al {light} y de noche. Pon una mojarra viva junto a los troncos.",
        "For a bigger fish, fish a live shad near drop-offs.": "Para un pez más grande, pesca una sardina viva cerca de los desniveles.",
        "Guadalupe bass feed heavily on crawfish.": "La lobina de Guadalupe come muchos acociles.",
        "Hybrids rarely pass up live shad or minnows.": "Las híbridas casi nunca dejan pasar sardina viva o pececillos.",
        "In bright midday sun the schools drop deeper. Jig a slab near the bottom.":
            "Con sol fuerte al mediodía los cardúmenes bajan más hondo. Jiggea un slab cerca del fondo.",
        "In bright sun stripers go deeper. Jig a heavy slab under the schools.":
            "Con sol fuerte la lobina rayada baja más hondo. Jiggea un slab pesado debajo de los cardúmenes.",
        "Jig it straight down over brush.": "Jiggéalo derecho hacia abajo sobre las ramas.",
        "Jig it under schools of bait.": "Jiggéalo debajo de los cardúmenes de carnada.",
        "Let it fall slowly along drop-offs.": "Déjalo caer despacio por los desniveles.",
        "Low light at {light}. A white or chartreuse jig shows up well.": "Poca luz al {light}. Un jig blanco o chartreuse se ve bien.",
        "Low light at {light}: bass come up and hit surface lures.": "Poca luz al {light}: la lobina sube y ataca señuelos de superficie.",
        "On bright days bluegill hang in shade by docks and brush. Fish a cricket under a bobber there.":
            "En días soleados la mojarra se queda en la sombra de muelles y ramas. Pesca un grillo bajo una boya ahí.",
        "On hot, sunny days Guadalupe bass go deeper. Fish a finesse worm slowly near rock.":
            "En días calientes y soleados la lobina de Guadalupe baja más hondo. Pesca un gusano finesse despacio cerca de las rocas.",
        "Rain or wind muddies the water: a spinnerbait's flash and vibration are easier to find.":
            "La lluvia o el viento enturbian el agua: el destello y la vibración de un spinnerbait se encuentran más fácil.",
        "Redear feed on snails on the bottom. Fish it slowly there.": "La mojarra de oreja roja come caracoles en el fondo. Péscalo despacio ahí.",
        "Retrieve slowly along the bank.": "Recoge despacio a lo largo de la orilla.",
        "Run it along the windblown bank to cover water quickly.": "Pásalo por la orilla del viento para recorrer agua rápido.",
        "Spotted bass favor small soft plastics. Drag it slowly near rock.":
            "La lobina manchada prefiere plásticos suaves pequeños. Arrástralo despacio cerca de las rocas.",
        "Stripers push bait to the surface at {light}. A big popper draws explosive strikes.":
            "La lobina rayada empuja la carnada a la superficie al {light}. Un popper grande provoca ataques explosivos.",
        "The classic smallmouth bait: let it sink, then hop it over rocky points.":
            "La carnada clásica para lobina de boca chica: déjala hundirse y luego hazla brincar sobre puntas rocosas.",
        "The easiest bite in the lake. Fish it under a bobber near the bank.": "El pique más fácil del lago. Péscalo bajo una boya cerca de la orilla.",
        "Their favorite food: fish it along the bottom near rock.": "Su comida favorita: péscalo por el fondo cerca de las rocas.",
        "When bass won't chase, a live shiner drifting past cover is hard for them to refuse.":
            "Cuando la lobina no persigue, un shiner vivo pasando junto al refugio es difícil de rechazar.",
        "Wind chop and cloud cover hide your line, and bass chase a moving, flashing bait.":
            "El oleaje y las nubes esconden tu línea, y la lobina persigue un señuelo que se mueve y destella.",
        "Wind pushes shad onto the windblown bank and white bass follow. Retrieve steadily along it.":
            "El viento empuja la sardina a la orilla del viento y la lobina blanca la sigue. Recoge parejo a lo largo de ella.",
        "Wind pushes shad onto the windblown bank. Fish cut shad on the bottom there.":
            "El viento empuja la sardina a la orilla del viento. Pesca sardina en trozos en el fondo ahí.",
        "Wind stirs up bait along the windblown bank. Swim a shad-like bait through it.":
            "El viento alborota la carnada en la orilla del viento. Pasa por ahí un señuelo que parezca sardina.",
        "With some wind or cloud, swim a stick worm along rocky banks and points.":
            "Con algo de viento o nubes, pasa un gusano tipo stick por orillas rocosas y puntas.",
        "Works almost anywhere catfish live.": "Funciona casi donde sea que viva el bagre.",
        "Works in almost any conditions. Fish it slowly near cover.": "Funciona casi en cualquier condición. Péscalo despacio cerca del refugio.",
        "Worms catch more drum than any other bait. Fish them on the bottom.":
            "Las lombrices sacan más corvinas que cualquier otra carnada. Péscalas en el fondo.",
        "A standard choice for this fish.": "Una opción común para este pez.",
        "A standard bait for this fish.": "Una carnada común para este pez.",
    },
    # Korean anglers' words: 미노우 for a live minnow, 바이브레이션 for a
    # lipless crankbait, 다운샷, 메탈 지그, 밑밥, 바람 받는 물가.
    "ko": {
        # names
        "1½–2½ in minnows": "1½~2½인치 미노우(생미끼)",
        "1½–2½ in minnows (the preferred bait)": "1½~2½인치 미노우(가장 좋은 미끼)",
        "1–2 oz slabs in chartreuse, chrome or white": "1~2온스 메탈 지그(차트, 크롬, 흰색)",
        "2–3 in curly-tail grubs on a jighead": "지그헤드에 2~3인치 컬리테일 그럽",
        "2–4 in live shad or fathead minnows": "2~4인치 살아 있는 섀드나 팻헤드 미노우",
        "2–4 in minnows or shad": "2~4인치 미노우나 섀드",
        "3–4 in tube on a 1/8–1/4 oz jighead": "1/8~1/4온스 지그헤드에 3~4인치 튜브 웜",
        "4–6 in straight-tail worms (green pumpkin or watermelon) on a shaky head or drop shot":
            "4~6인치 스트레이트 웜(그린펌킨 또는 워터멜론), 셰이키헤드나 다운샷 채비로",
        "5 in stick-style worms": "5인치 스틱 웜",
        "6 in pencil poppers (topwater)": "6인치 펜슬 포퍼(탑워터)",
        "A small piece of worm or nightcrawler, just enough to cover the hook": "바늘이 가려질 만큼의 작은 지렁이 조각",
        "Beetle-spins": "비틀스핀(스피너가 달린 지그)",
        "Bucktail jigs": "벅테일 지그",
        "Canned or frozen sweet corn": "통조림이나 냉동 스위트콘",
        "Chicken liver": "닭 간",
        "Crankbaits and ¼–½ oz lipless crankbaits": "크랭크베이트와 ¼~½온스 바이브레이션",
        "Crawdad tails": "가재 꼬리",
        "Crayfish": "가재",
        "Crickets": "귀뚜라미",
        "Dough baits such as PowerBait, molded to cover the hook": "파워베이트 같은 떡밥(바늘을 감싸도록 뭉치기)",
        "Dough balls and oatmeal-based pack baits": "떡밥 경단과 오트밀 집어제",
        "Drop-shot finesse worms": "다운샷 피네스 웜",
        "Fresh cut shad (fresh beats frozen)": "싱싱한 섀드 토막(냉동보다 생물이 좋아요)",
        "Grubs on 1/8–½ oz jigheads": "1/8~½온스 지그헤드에 그럽",
        "Inline spinners": "인라인 스피너",
        "Jerkbaits, and topwater lures twitched like an injured fish": "저크베이트, 그리고 다친 물고기처럼 트위칭하는 탑워터 루어",
        "Jigs": "지그(러버 지그)",
        "Large live minnows, goldfish or bullheads": "큰 살아 있는 미노우, 금붕어나 작은 메기(불헤드)",
        "Large live shiners (8–9 in) under a bobber": "찌 아래에 큰 살아 있는 샤이너(8~9인치)",
        "Live shad": "살아 있는 섀드",
        "Live sunfish, such as bluegill (the go-to bait)": "블루길 같은 살아 있는 선피시(대표 미끼)",
        "Live threadfin or gizzard shad": "살아 있는 스레드핀섀드나 기자드섀드",
        "Ned rig (a short soft-plastic stick on a small jighead) bounced along the bottom":
            "네드 리그(작은 지그헤드에 짧은 스틱 웜), 바닥을 톡톡 튀기며",
        "Ned rig: a 3–4 in stick worm on a 1/8–1/4 oz mushroom jighead": "네드 리그: 1/8~1/4온스 머시룸 지그헤드에 3~4인치 스틱 웜",
        "Nightcrawlers": "큰 지렁이(나이트크롤러)",
        "Plastic worms": "웜",
        "Poppers and other topwaters near downed trees and lily pads": "쓰러진 나무와 연잎 근처에서 포퍼 등 탑워터 루어",
        "Redworms or other earthworms": "줄지렁이 등 지렁이",
        "Shrimp (stays on the hook well)": "새우(바늘에서 잘 안 빠져요)",
        "Slabs and jigging spoons": "메탈 지그와 지깅 스푼",
        "Small black or brown jigs that look like a snail or insect": "고둥이나 벌레처럼 보이는 검은색·갈색 작은 지그",
        "Small crankbaits": "작은 크랭크베이트",
        "Small grubs and jigs fished near the bottom": "바닥 가까이에서 쓰는 작은 그럽과 지그",
        "Small inline spinners, 1/16–1/8 oz (olive, brown, black or white)": "1/16~1/8온스 작은 인라인 스피너(올리브, 갈색, 검은색, 흰색)",
        "Small jigging spoons": "작은 지깅 스푼",
        "Small jigs and soft-plastic crawfish": "작은 지그와 가재 모양 웜",
        "Small pieces of worm": "작은 지렁이 조각",
        "Small poppers": "작은 포퍼",
        "Small poppers at dawn or dusk": "새벽이나 해 질 녘에 작은 포퍼",
        "Small soft-plastic jigs": "작은 웜 지그",
        "Small spoons in gold or silver": "금색이나 은색 작은 스푼",
        "Spinnerbaits": "스피너베이트",
        "Spinnerbaits, heavier ones in current": "스피너베이트(물살이 있으면 무거운 것)",
        "Stinkbait": "냄새 미끼(스팅크베이트)",
        "Swimbaits": "스윔베이트",
        "Tiny jigs, 1/32 oz and smaller (black works well)": "1/32온스 이하 아주 작은 지그(검은색이 잘 먹혀요)",
        "Tiny spinners": "아주 작은 스피너",
        "Topwater lures": "탑워터 루어",
        "Topwater lures when schools are breaking the surface": "무리가 수면에서 보일링할 때는 탑워터 루어",
        "Wax worms": "왁스웜",
        "White or chartreuse marabou jigs in low light": "어두울 때는 흰색이나 차트 색 마라부 지그",
        "Worms and nightcrawlers": "지렁이와 큰 지렁이",
        "¼–1 oz slabs": "¼~1온스 메탈 지그",
        "½ oz lipless crankbaits": "½온스 바이브레이션",
        # why
        "A bit of flash gets noticed in choppy or cloudy water.": "물결이 일거나 흐린 날에는 약간의 반짝임이 눈에 잘 띄어요.",
        "A classic catfish bait. Fish it on the bottom.": "메기 낚시의 대표 미끼예요. 바닥에 가라앉혀서 낚으세요.",
        "A dependable all-round striper lure.": "스트라이프드배스에 두루 믿고 쓰는 루어예요.",
        "A flashing spinner stands out in choppy or cloudy water.": "물결이 일거나 흐린 날에는 반짝이는 스피너가 눈에 띄어요.",
        "A flathead eats only live fish. Fish a live sunfish tight to heavy wood cover.":
            "플랫헤드메기는 살아 있는 물고기만 먹어요. 살아 있는 선피시를 굵은 나무 커버에 바짝 붙여 주세요.",
        "A front is on the way, and bass often feed hard before it. Cover water fast.":
            "전선이 다가오고 있어요. 배스는 전선이 오기 전에 활발히 먹으니, 빠르게 넓게 탐색하세요.",
        "A good search bait for finding active fish.": "활성도 높은 물고기를 찾기 좋은 탐색용 루어예요.",
        "A little flash helps in choppy or cloudy water. Retrieve slowly.": "물결이 일거나 흐린 날에는 약간의 반짝임이 도움이 돼요. 천천히 감으세요.",
        "A minnow under a bobber near cover. Crappie's favorite meal.": "커버 근처에서 찌 아래에 미노우를 다세요. 크래피가 가장 좋아하는 먹이예요.",
        "A popular, simple way to fish a river pool.": "강의 깊은 소를 노리는, 간단하고 인기 있는 방법이에요.",
        "A small bait for a small mouth; fish it near the bottom.": "입이 작으니 작은 미끼를 쓰세요. 바닥 가까이에서 낚아요.",
        "A small piece of worm on a small hook works for trout.": "작은 바늘에 지렁이 조각을 달면 송어가 잡혀요.",
        "A small spoon catches stocked trout too.": "방류한 송어는 작은 스푼으로도 잡혀요.",
        "An easy all-round choice. Cast and retrieve steadily.": "쉽고 두루 쓰기 좋아요. 던지고 일정한 속도로 감으세요.",
        "At {light} crappie rise to feed. A small popper can draw strikes on top.":
            "{light}에는 크래피가 떠올라 먹이를 먹어요. 작은 포퍼로 수면 입질을 받을 수 있어요.",
        "At {light}, schools chase shad to the surface. Watch for splashes and cast into them.":
            "{light}에는 무리가 섀드를 수면까지 몰아요. 물보라가 보이면 그곳으로 던지세요.",
        "At {light}, smallmouth hunt the shallows: twitch a surface lure over rock.":
            "{light}에는 작은입배스가 얕은 곳에서 사냥해요. 바위 위에서 탑워터 루어를 트위칭하세요.",
        "At {light}, work a popper along shady banks, downed trees and lily pads.":
            "{light}에는 그늘진 물가, 쓰러진 나무, 연잎을 따라 포퍼를 움직이세요.",
        "Bigger live bait tends to catch bigger flatheads.": "생미끼가 클수록 큰 플랫헤드메기가 잡히는 편이에요.",
        "Blue catfish are caught on bait. No lure needed.": "블루메기는 미끼로 잡아요. 루어는 필요 없어요.",
        "Blue cats hunt by smell. Fresh cut shad on the bottom is the standard.":
            "블루메기는 냄새로 먹이를 찾아요. 싱싱한 섀드 토막을 바닥에 두는 게 정석이에요.",
        "Bluegill feed at the surface at {light}. A small popper is fun and effective.":
            "{light}에는 블루길이 수면에서 먹이를 먹어요. 작은 포퍼는 재미있고 잘 먹혀요.",
        "Bright sun pushes bass tight to cover. Pitch a jig right into it.": "햇빛이 강하면 배스는 커버에 바짝 붙어요. 지그를 그 안으로 바로 피칭하세요.",
        "Bright sun pushes crappie into shade. Drop a small jig next to docks and brush.":
            "햇빛이 강하면 크래피는 그늘로 숨어요. 선착장과 나뭇가지 더미 옆에 작은 지그를 내려 주세요.",
        "Bright sun sends hybrids deeper. Fish a slab straight down.": "햇빛이 강하면 하이브리드는 더 깊이 내려가요. 메탈 지그를 바로 아래로 내려 낚으세요.",
        "Calm, bright water makes bass cautious. Crawl a worm slowly through cover.":
            "바람 없고 밝은 날에는 배스가 경계해요. 커버 사이로 웜을 천천히 기어가게 하세요.",
        "Carp find a scented bait on the bottom; mold it to hide the hook.": "잉어는 바닥에서 냄새 나는 미끼를 찾아요. 바늘이 안 보이게 감싸서 뭉치세요.",
        "Carp rarely strike lures. Fish bait on the bottom.": "잉어는 루어를 거의 안 물어요. 미끼를 바닥에 두고 낚으세요.",
        "Cast and retrieve slowly along the bank.": "물가를 따라 던지고 천천히 감으세요.",
        "Casting in wind tears soft baits off. Shrimp stays on the hook.": "바람 속에서 던지면 부드러운 미끼는 떨어져 나가요. 새우는 바늘에 잘 붙어 있어요.",
        "Catfish are caught on bait. No lure needed.": "메기는 미끼로 잡아요. 루어는 필요 없어요.",
        "Catfish are still feeding after the night. Fish a nightcrawler on the bottom.": "메기는 밤이 지나도 아직 먹이를 먹고 있어요. 큰 지렁이를 바닥에 두세요.",
        "Chum a few handfuls of corn, then fish corn on the bottom over it.": "옥수수를 몇 줌 밑밥으로 뿌린 다음, 그 위에서 옥수수를 바닥에 두고 낚으세요.",
        "Clear, bright conditions. A small finesse worm near rock gets bit when bigger baits don't.":
            "맑고 밝은 날이에요. 큰 루어에 반응이 없을 때도 바위 근처의 작은 피네스 웜에는 입질이 와요.",
        "Clear, bright water: smallmouth see well, so a small, slow finesse bait near rock gets bit.":
            "물이 맑고 밝아요. 작은입배스가 잘 보니, 바위 근처에서 작은 피네스 루어를 천천히 쓰면 입질이 와요.",
        "Clouds and rain put catfish on the move, and a strong-smelling bait helps them find it.":
            "흐리거나 비가 오면 메기가 돌아다니고, 냄새가 강한 미끼일수록 찾기 쉬워요.",
        "Cover water fast along the windblown side, where shad gather.": "섀드가 모이는, 바람을 받는 쪽을 빠르게 넓게 탐색하세요.",
        "Covers water fast to find a school.": "넓은 범위를 빠르게 탐색해 무리를 찾아요.",
        "Covers water quickly to find a school.": "빠르게 넓게 훑어서 무리를 찾아요.",
        "Covers water to find a school.": "넓게 탐색해 무리를 찾아요.",
        "Drag it slowly over rock, pausing a few seconds.": "바위 위를 천천히 끌다가 몇 초씩 멈추세요.",
        "Drift live shad where you find fish. The most reliable way to catch stripers.":
            "물고기가 있는 곳에서 살아 있는 섀드를 흘려보내세요. 스트라이프드배스를 가장 확실하게 잡는 방법이에요.",
        "Drum feed on the bottom. Work it slowly near current breaks.": "드럼은 바닥에서 먹이를 먹어요. 물살이 꺾이는 곳 근처에서 천천히 움직이세요.",
        "Drum root along the bottom for crayfish.": "드럼은 바닥을 뒤지며 가재를 찾아요.",
        "Easy and reliable: cast, let it sink, retrieve steadily.": "쉽고 확실해요. 던지고, 가라앉히고, 일정하게 감으세요.",
        "Fish it next to cover. Bass take a real shiner faster than any plastic.": "커버 옆에서 쓰세요. 배스는 어떤 웜보다 진짜 샤이너를 더 빨리 물어요.",
        "Fish it on or just off the bottom, a little deeper than the bluegill beds.":
            "바닥이나 바닥 바로 위에서, 블루길 산란장보다 조금 깊은 곳을 노리세요.",
        "Fish it on the bottom and wait for steady pressure: trout often nibble first.":
            "바닥에 두고 꾹 당기는 느낌이 올 때까지 기다리세요. 송어는 처음에 톡톡 건드리는 경우가 많아요.",
        "Fish it slowly near brush piles, docks and bridge pilings.": "나뭇가지 더미, 선착장, 교각 근처에서 천천히 낚으세요.",
        "Fish it slowly near weeds and docks.": "수초와 선착장 근처에서 천천히 낚으세요.",
        "Fish it where you find a school, under a bobber or on a light weight.": "무리를 찾으면 그곳에서 찌나 가벼운 봉돌로 낚으세요.",
        "Flatheads consistently take only live bait. No lure needed.": "플랫헤드메기는 거의 생미끼만 먹어요. 루어는 필요 없어요.",
        "Flatheads move shallow to feed at {light} and after dark. Put a live sunfish next to wood cover.":
            "{light}, 그리고 해가 진 뒤에 플랫헤드메기가 얕은 곳으로 나와 먹이를 먹어요. 나무 커버 옆에 살아 있는 선피시를 두세요.",
        "For a bigger fish, fish a live shad near drop-offs.": "큰 물고기를 노린다면 브레이크라인 근처에서 살아 있는 섀드를 쓰세요.",
        "Guadalupe bass feed heavily on crawfish.": "과달루페배스는 가재를 아주 많이 먹어요.",
        "Hybrids rarely pass up live shad or minnows.": "하이브리드는 살아 있는 섀드나 미노우를 좀처럼 그냥 두지 않아요.",
        "In bright midday sun the schools drop deeper. Jig a slab near the bottom.": "햇빛이 강한 한낮에는 무리가 더 깊이 내려가요. 바닥 근처에서 메탈 지그를 저킹하세요.",
        "In bright sun stripers go deeper. Jig a heavy slab under the schools.":
            "햇빛이 강하면 스트라이프드배스는 더 깊이 내려가요. 무리 아래에서 무거운 메탈 지그를 저킹하세요.",
        "Jig it straight down over brush.": "나뭇가지 더미 바로 위에서 위아래로 저킹하세요.",
        "Jig it under schools of bait.": "베이트피시 무리 아래에서 저킹하세요.",
        "Let it fall slowly along drop-offs.": "브레이크라인을 따라 천천히 폴링시키세요.",
        "Low light at {light}. A white or chartreuse jig shows up well.": "{light}에는 빛이 약해서 흰색이나 차트 색 지그가 잘 보여요.",
        "Low light at {light}: bass come up and hit surface lures.": "{light}에는 빛이 약해서 배스가 떠올라 탑워터 루어를 공격해요.",
        "On bright days bluegill hang in shade by docks and brush. Fish a cricket under a bobber there.":
            "맑은 날 블루길은 선착장과 나뭇가지 더미의 그늘에 머물러요. 그곳에서 찌 아래에 귀뚜라미를 달아 보세요.",
        "On hot, sunny days Guadalupe bass go deeper. Fish a finesse worm slowly near rock.":
            "덥고 맑은 날 과달루페배스는 더 깊이 내려가요. 바위 근처에서 피네스 웜을 천천히 쓰세요.",
        "Rain or wind muddies the water: a spinnerbait's flash and vibration are easier to find.":
            "비나 바람으로 물이 탁해지면, 물고기가 스피너베이트의 반짝임과 진동을 더 쉽게 찾아요.",
        "Redear feed on snails on the bottom. Fish it slowly there.": "레드이어선피시는 바닥에서 고둥을 먹어요. 그곳에서 천천히 낚으세요.",
        "Retrieve slowly along the bank.": "물가를 따라 천천히 감으세요.",
        "Run it along the windblown bank to cover water quickly.": "바람을 받는 물가를 따라 끌어서 빠르게 넓게 탐색하세요.",
        "Spotted bass favor small soft plastics. Drag it slowly near rock.": "스포티드배스는 작은 웜을 좋아해요. 바위 근처에서 천천히 끄세요.",
        "Stripers push bait to the surface at {light}. A big popper draws explosive strikes.":
            "{light}에는 스트라이프드배스가 베이트피시를 수면으로 몰아요. 큰 포퍼에 폭발적인 입질이 와요.",
        "The classic smallmouth bait: let it sink, then hop it over rocky points.": "작은입배스의 대표 루어예요. 가라앉힌 다음 바위 곶부리 위에서 호핑하세요.",
        "The easiest bite in the lake. Fish it under a bobber near the bank.": "호수에서 가장 쉽게 입질을 받는 미끼예요. 물가 가까이에서 찌낚시로 쓰세요.",
        "Their favorite food: fish it along the bottom near rock.": "가장 좋아하는 먹이예요. 바위 근처 바닥을 따라 낚으세요.",
        "When bass won't chase, a live shiner drifting past cover is hard for them to refuse.":
            "배스가 쫓지 않을 때도, 커버 옆을 흘러가는 살아 있는 샤이너는 그냥 지나치기 어려워요.",
        "Wind chop and cloud cover hide your line, and bass chase a moving, flashing bait.":
            "바람 물결과 구름이 낚싯줄을 가려 주고, 배스는 움직이며 반짝이는 루어를 쫓아요.",
        "Wind pushes shad onto the windblown bank and white bass follow. Retrieve steadily along it.":
            "바람이 섀드를 바람 받는 물가로 몰고, 화이트배스가 그 뒤를 따라가요. 그 물가를 따라 일정하게 감으세요.",
        "Wind pushes shad onto the windblown bank. Fish cut shad on the bottom there.": "바람이 섀드를 바람 받는 물가로 몰아요. 그곳 바닥에 섀드 토막을 두세요.",
        "Wind stirs up bait along the windblown bank. Swim a shad-like bait through it.":
            "바람 받는 물가에서는 바람이 베이트피시를 휘저어요. 섀드를 닮은 루어를 그곳으로 지나가게 하세요.",
        "With some wind or cloud, swim a stick worm along rocky banks and points.": "바람이 조금 있거나 흐리면, 바위 물가와 곶부리를 따라 스틱 웜을 헤엄치게 하세요.",
        "Works almost anywhere catfish live.": "메기가 사는 곳이면 거의 어디서나 잘 먹혀요.",
        "Works in almost any conditions. Fish it slowly near cover.": "거의 어떤 조건에서도 잘 먹혀요. 커버 근처에서 천천히 낚으세요.",
        "Worms catch more drum than any other bait. Fish them on the bottom.": "드럼은 어떤 미끼보다 지렁이로 많이 잡혀요. 바닥에 두고 낚으세요.",
        "A standard choice for this fish.": "이 어종에 흔히 쓰는 선택이에요.",
        "A standard bait for this fish.": "이 어종에 흔히 쓰는 미끼예요.",
    },
    # Japanese anglers' words: 小魚 for a live minnow (a ミノー is a lure),
    # バイブレーション, ダウンショット, メタルジグ, ボイル, かけ上がり, 流れのヨレ.
    "ja": {
        # names
        "1½–2½ in minnows": "1½〜2½インチの小魚（生きエサ）",
        "1½–2½ in minnows (the preferred bait)": "1½〜2½インチの小魚（いちばんのエサ）",
        "1–2 oz slabs in chartreuse, chrome or white": "1〜2オンスのメタルジグ（チャート、クローム、白）",
        "2–3 in curly-tail grubs on a jighead": "ジグヘッドに2〜3インチのカーリーテールグラブ",
        "2–4 in live shad or fathead minnows": "2〜4インチの生きたシャッドかファットヘッドミノー",
        "2–4 in minnows or shad": "2〜4インチの小魚かシャッド",
        "3–4 in tube on a 1/8–1/4 oz jighead": "1/8〜1/4オンスのジグヘッドに3〜4インチのチューブワーム",
        "4–6 in straight-tail worms (green pumpkin or watermelon) on a shaky head or drop shot":
            "4〜6インチのストレートワーム（グリーンパンプキンかウォーターメロン）をシェイキーヘッドかダウンショットで",
        "5 in stick-style worms": "5インチのスティック系ワーム",
        "6 in pencil poppers (topwater)": "6インチのペンシルポッパー（トップウォーター）",
        "A small piece of worm or nightcrawler, just enough to cover the hook": "針が隠れるくらいの小さなミミズの切れ端",
        "Beetle-spins": "ビートルスピン（スピナー付きジグ）",
        "Bucktail jigs": "バックテールジグ",
        "Canned or frozen sweet corn": "缶詰か冷凍のスイートコーン",
        "Chicken liver": "鶏レバー",
        "Crankbaits and ¼–½ oz lipless crankbaits": "クランクベイトと¼〜½オンスのバイブレーション",
        "Crawdad tails": "ザリガニのしっぽ",
        "Crayfish": "ザリガニ",
        "Crickets": "コオロギ",
        "Dough baits such as PowerBait, molded to cover the hook": "パワーベイトなどの練りエサ（針を包むように丸める）",
        "Dough balls and oatmeal-based pack baits": "練りエサの団子と、オートミールベースの寄せエサ",
        "Drop-shot finesse worms": "ダウンショットのフィネスワーム",
        "Fresh cut shad (fresh beats frozen)": "新鮮なシャッドの切り身（冷凍より生がよい）",
        "Grubs on 1/8–½ oz jigheads": "1/8〜½オンスのジグヘッドにグラブ",
        "Inline spinners": "インラインスピナー",
        "Jerkbaits, and topwater lures twitched like an injured fish": "ジャークベイトと、弱った小魚のようにトゥイッチするトップウォーター",
        "Jigs": "ジグ（ラバージグ）",
        "Large live minnows, goldfish or bullheads": "大きめの生きた小魚、金魚、小型のナマズ（ブルヘッド）",
        "Large live shiners (8–9 in) under a bobber": "ウキの下に大きな生きたシャイナー（8〜9インチ）",
        "Live shad": "生きたシャッド",
        "Live sunfish, such as bluegill (the go-to bait)": "ブルーギルなど生きたサンフィッシュ（定番のエサ）",
        "Live threadfin or gizzard shad": "生きたスレッドフィンシャッドかギザードシャッド",
        "Ned rig (a short soft-plastic stick on a small jighead) bounced along the bottom":
            "ネドリグ（小さなジグヘッドに短いスティックワーム）で底を跳ねさせる",
        "Ned rig: a 3–4 in stick worm on a 1/8–1/4 oz mushroom jighead": "ネドリグ：1/8〜1/4オンスのマッシュルームジグヘッドに3〜4インチのスティックワーム",
        "Nightcrawlers": "ドバミミズ",
        "Plastic worms": "ワーム",
        "Poppers and other topwaters near downed trees and lily pads": "倒木やスイレンの近くでポッパーなどのトップウォーター",
        "Redworms or other earthworms": "シマミミズなどのミミズ",
        "Shrimp (stays on the hook well)": "エビ（針から外れにくい）",
        "Slabs and jigging spoons": "メタルジグとジギングスプーン",
        "Small black or brown jigs that look like a snail or insect": "巻貝や虫に見える、黒か茶色の小さなジグ",
        "Small crankbaits": "小型クランクベイト",
        "Small grubs and jigs fished near the bottom": "底近くで使う小さなグラブとジグ",
        "Small inline spinners, 1/16–1/8 oz (olive, brown, black or white)": "1/16〜1/8オンスの小さなインラインスピナー（オリーブ、茶、黒、白）",
        "Small jigging spoons": "小型のジギングスプーン",
        "Small jigs and soft-plastic crawfish": "小さなジグとザリガニ型のワーム",
        "Small pieces of worm": "ミミズの切れ端",
        "Small poppers": "小型ポッパー",
        "Small poppers at dawn or dusk": "明け方や夕暮れに小型ポッパー",
        "Small soft-plastic jigs": "小型のワームジグ",
        "Small spoons in gold or silver": "金か銀の小型スプーン",
        "Spinnerbaits": "スピナーベイト",
        "Spinnerbaits, heavier ones in current": "スピナーベイト（流れがあるときは重めを）",
        "Stinkbait": "においエサ（スティンクベイト）",
        "Swimbaits": "スイムベイト",
        "Tiny jigs, 1/32 oz and smaller (black works well)": "1/32オンス以下の極小ジグ（黒がよく効く）",
        "Tiny spinners": "極小スピナー",
        "Topwater lures": "トップウォータールアー",
        "Topwater lures when schools are breaking the surface": "群れが水面でボイルしているときはトップウォーター",
        "Wax worms": "ブドウムシ",
        "White or chartreuse marabou jigs in low light": "暗いときは白かチャートのマラブージグ",
        "Worms and nightcrawlers": "ミミズとドバミミズ",
        "¼–1 oz slabs": "¼〜1オンスのメタルジグ",
        "½ oz lipless crankbaits": "½オンスのバイブレーション",
        # why
        "A bit of flash gets noticed in choppy or cloudy water.": "波立った水面や曇りの日は、少しのフラッシングが目立ちます。",
        "A classic catfish bait. Fish it on the bottom.": "ナマズの定番のエサ。底に沈めて釣ります。",
        "A dependable all-round striper lure.": "ストライプドバスに、どんな状況でも頼れるルアー。",
        "A flashing spinner stands out in choppy or cloudy water.": "波立った水面や曇りの日は、光るスピナーが目立ちます。",
        "A flathead eats only live fish. Fish a live sunfish tight to heavy wood cover.":
            "フラットヘッドは生きた魚しか食べません。生きたサンフィッシュを太い木のカバーにぴったり付けて。",
        "A front is on the way, and bass often feed hard before it. Cover water fast.":
            "前線が近づいていて、バスはその前によく食います。テンポよく広く探りましょう。",
        "A good search bait for finding active fish.": "活性の高い魚を探すのにいいサーチベイト。",
        "A little flash helps in choppy or cloudy water. Retrieve slowly.": "波立ちや曇りの日は少しのフラッシングが効きます。ゆっくり巻いて。",
        "A minnow under a bobber near cover. Crappie's favorite meal.": "カバーの近くで、ウキの下に小魚を。クラッピーの大好物です。",
        "A popular, simple way to fish a river pool.": "川の淵を釣る、手軽で人気の方法。",
        "A small bait for a small mouth; fish it near the bottom.": "口が小さいので小さなエサを。底近くで釣ります。",
        "A small piece of worm on a small hook works for trout.": "小さな針にミミズの切れ端で、マスが釣れます。",
        "A small spoon catches stocked trout too.": "放流マスには小型スプーンも効きます。",
        "An easy all-round choice. Cast and retrieve steadily.": "簡単で万能。投げて、一定の速さで巻きます。",
        "At {light} crappie rise to feed. A small popper can draw strikes on top.":
            "{light}はクラッピーが浮いてエサを追います。小型ポッパーで水面のバイトが出ることも。",
        "At {light}, schools chase shad to the surface. Watch for splashes and cast into them.":
            "{light}は群れがシャッドを水面まで追い上げます。水しぶきを見つけたら、そこへ投げて。",
        "At {light}, smallmouth hunt the shallows: twitch a surface lure over rock.":
            "{light}はスモールマウスが浅場で狩りをします。岩の上でトップウォーターをトゥイッチ。",
        "At {light}, work a popper along shady banks, downed trees and lily pads.":
            "{light}は日陰の岸、倒木、スイレンに沿ってポッパーを動かします。",
        "Bigger live bait tends to catch bigger flatheads.": "生きエサが大きいほど、大きなフラットヘッドが釣れやすくなります。",
        "Blue catfish are caught on bait. No lure needed.": "ブルーキャットフィッシュはエサで釣ります。ルアーは不要です。",
        "Blue cats hunt by smell. Fresh cut shad on the bottom is the standard.":
            "ブルーキャットはにおいでエサを探します。新鮮なシャッドの切り身を底に置くのが定番。",
        "Bluegill feed at the surface at {light}. A small popper is fun and effective.":
            "{light}はブルーギルが水面でエサをとります。小型ポッパーは楽しくてよく釣れます。",
        "Bright sun pushes bass tight to cover. Pitch a jig right into it.": "日差しが強いとバスはカバーに張り付きます。ジグを中へ直接ピッチング。",
        "Bright sun pushes crappie into shade. Drop a small jig next to docks and brush.":
            "日差しが強いとクラッピーは日陰に入ります。桟橋や沈んだ枝の脇に小さなジグを落として。",
        "Bright sun sends hybrids deeper. Fish a slab straight down.": "日差しが強いとハイブリッドは深場へ。メタルジグを真下に落として釣ります。",
        "Calm, bright water makes bass cautious. Crawl a worm slowly through cover.":
            "無風で明るいと、バスは警戒します。カバーの中をワームでゆっくりずる引き。",
        "Carp find a scented bait on the bottom; mold it to hide the hook.": "コイは底にあるにおいのエサを見つけます。針を包んで隠すように丸めて。",
        "Carp rarely strike lures. Fish bait on the bottom.": "コイはめったにルアーを食いません。エサを底で釣ります。",
        "Cast and retrieve slowly along the bank.": "岸沿いに投げて、ゆっくり巻きます。",
        "Casting in wind tears soft baits off. Shrimp stays on the hook.": "風の中で投げると柔らかいエサは外れがち。エビなら針に残ります。",
        "Catfish are caught on bait. No lure needed.": "ナマズはエサで釣ります。ルアーは不要です。",
        "Catfish are still feeding after the night. Fish a nightcrawler on the bottom.": "ナマズは夜が明けてもまだエサを食べています。ドバミミズを底で。",
        "Chum a few handfuls of corn, then fish corn on the bottom over it.": "コーンを何握りかまいて魚を寄せ、その上でコーンを底に置いて釣ります。",
        "Clear, bright conditions. A small finesse worm near rock gets bit when bigger baits don't.":
            "晴れて水も澄んでいます。大きなルアーに反応がないときも、岩の近くの小さなフィネスワームなら食います。",
        "Clear, bright water: smallmouth see well, so a small, slow finesse bait near rock gets bit.":
            "澄んで明るい水では、スモールマウスはよく見えています。岩の近くで小さなフィネスベイトをゆっくり。",
        "Clouds and rain put catfish on the move, and a strong-smelling bait helps them find it.":
            "曇りや雨でナマズは動き回り、においの強いエサほど見つけてもらいやすくなります。",
        "Cover water fast along the windblown side, where shad gather.": "シャッドが集まる、風が当たる側をテンポよく広く探ります。",
        "Covers water fast to find a school.": "広く速く探って、群れを見つけます。",
        "Covers water quickly to find a school.": "手早く広範囲を探って、群れを見つけます。",
        "Covers water to find a school.": "広く探って、群れを見つけます。",
        "Drag it slowly over rock, pausing a few seconds.": "岩の上をゆっくりずる引きし、ときどき数秒止めます。",
        "Drift live shad where you find fish. The most reliable way to catch stripers.":
            "魚がいる場所で生きたシャッドを流します。ストライプドバスをいちばん確実に釣る方法。",
        "Drum feed on the bottom. Work it slowly near current breaks.": "ドラムは底でエサをとります。流れのヨレの近くでゆっくり動かして。",
        "Drum root along the bottom for crayfish.": "ドラムは底をあさってザリガニを探します。",
        "Easy and reliable: cast, let it sink, retrieve steadily.": "簡単で確実：投げて、沈めて、一定の速さで巻くだけ。",
        "Fish it next to cover. Bass take a real shiner faster than any plastic.": "カバーの脇で。バスはどんなワームより、本物のシャイナーに素早く食いつきます。",
        "Fish it on or just off the bottom, a little deeper than the bluegill beds.":
            "底かその少し上で、ブルーギルの産卵床より少し深いところを釣ります。",
        "Fish it on the bottom and wait for steady pressure: trout often nibble first.":
            "底に置いて、しっかり引き込まれるまで待ちます。マスは最初につつくことが多いです。",
        "Fish it slowly near brush piles, docks and bridge pilings.": "沈んだ枝の山、桟橋、橋脚の近くでゆっくり釣ります。",
        "Fish it slowly near weeds and docks.": "水草や桟橋の近くでゆっくり釣ります。",
        "Fish it where you find a school, under a bobber or on a light weight.": "群れを見つけたら、ウキか軽いオモリでそこを釣ります。",
        "Flatheads consistently take only live bait. No lure needed.": "フラットヘッドが食うのはほぼ生きエサだけ。ルアーは不要です。",
        "Flatheads move shallow to feed at {light} and after dark. Put a live sunfish next to wood cover.":
            "{light}と日が暮れたあと、フラットヘッドは浅場に出てエサをとります。木のカバーの脇に生きたサンフィッシュを。",
        "For a bigger fish, fish a live shad near drop-offs.": "大物狙いなら、かけ上がりの近くで生きたシャッドを。",
        "Guadalupe bass feed heavily on crawfish.": "グアダルーペバスはザリガニをよく食べます。",
        "Hybrids rarely pass up live shad or minnows.": "ハイブリッドは、生きたシャッドや小魚をまず見逃しません。",
        "In bright midday sun the schools drop deeper. Jig a slab near the bottom.": "日差しの強い昼は群れが深く沈みます。底近くでメタルジグをしゃくって。",
        "In bright sun stripers go deeper. Jig a heavy slab under the schools.":
            "日差しが強いとストライプドバスは深場へ。群れの下で重いメタルジグをしゃくります。",
        "Jig it straight down over brush.": "沈んだ枝の真上で、上下にしゃくります。",
        "Jig it under schools of bait.": "ベイトの群れの下でしゃくります。",
        "Let it fall slowly along drop-offs.": "かけ上がりに沿って、ゆっくりフォールさせます。",
        "Low light at {light}. A white or chartreuse jig shows up well.": "{light}は光が弱いので、白やチャートのジグがよく目立ちます。",
        "Low light at {light}: bass come up and hit surface lures.": "{light}は光が弱く、バスが浮いてきてトップウォーターに出ます。",
        "On bright days bluegill hang in shade by docks and brush. Fish a cricket under a bobber there.":
            "晴れた日のブルーギルは、桟橋や沈んだ枝の日陰にいます。そこでウキの下にコオロギを。",
        "On hot, sunny days Guadalupe bass go deeper. Fish a finesse worm slowly near rock.":
            "暑く晴れた日、グアダルーペバスは深場へ。岩の近くでフィネスワームをゆっくり。",
        "Rain or wind muddies the water: a spinnerbait's flash and vibration are easier to find.":
            "雨や風で水が濁ると、スピナーベイトのフラッシングと振動が魚に見つけてもらいやすくなります。",
        "Redear feed on snails on the bottom. Fish it slowly there.": "レッドイヤーは底で巻貝を食べます。そこでゆっくり釣ります。",
        "Retrieve slowly along the bank.": "岸沿いにゆっくり巻きます。",
        "Run it along the windblown bank to cover water quickly.": "風が当たる岸沿いに通して、手早く広く探ります。",
        "Spotted bass favor small soft plastics. Drag it slowly near rock.": "スポッテッドバスは小さなワームが好み。岩の近くでゆっくりずる引き。",
        "Stripers push bait to the surface at {light}. A big popper draws explosive strikes.":
            "{light}はストライプドバスがベイトを水面に追い込みます。大きなポッパーに豪快なバイトが出ます。",
        "The classic smallmouth bait: let it sink, then hop it over rocky points.": "スモールマウスの定番：沈めてから、岩の岬の上でホップさせます。",
        "The easiest bite in the lake. Fish it under a bobber near the bank.": "湖でいちばん簡単に釣れるエサ。岸の近くでウキ釣りに。",
        "Their favorite food: fish it along the bottom near rock.": "大好物です。岩の近くの底を釣ります。",
        "When bass won't chase, a live shiner drifting past cover is hard for them to refuse.":
            "バスが追わないときでも、カバーの脇を流れる生きたシャイナーには口を使いやすいもの。",
        "Wind chop and cloud cover hide your line, and bass chase a moving, flashing bait.":
            "風の波と雲がラインを隠し、バスは動いて光るルアーを追います。",
        "Wind pushes shad onto the windblown bank and white bass follow. Retrieve steadily along it.":
            "風がシャッドを風の当たる岸へ寄せ、ホワイトバスがそれを追います。その岸沿いを一定の速さで巻いて。",
        "Wind pushes shad onto the windblown bank. Fish cut shad on the bottom there.": "風がシャッドを風の当たる岸へ寄せます。そこでシャッドの切り身を底に置いて。",
        "Wind stirs up bait along the windblown bank. Swim a shad-like bait through it.":
            "風の当たる岸では、ベイトがかき回されています。シャッドに似たルアーをそこで泳がせて。",
        "With some wind or cloud, swim a stick worm along rocky banks and points.": "少し風があるか曇っていれば、岩の岸や岬に沿ってスティックワームを泳がせます。",
        "Works almost anywhere catfish live.": "ナマズがいる所なら、ほぼどこでも効きます。",
        "Works in almost any conditions. Fish it slowly near cover.": "ほとんどの条件で効きます。カバーの近くでゆっくり釣って。",
        "Worms catch more drum than any other bait. Fish them on the bottom.": "ドラムはミミズでいちばんよく釣れます。底で釣ります。",
        "A standard choice for this fish.": "この魚の定番。",
        "A standard bait for this fish.": "この魚の定番のエサ。",
    },
}


def tr(text: str | None, lang: str) -> str | None:
    """`text` in `lang`, or as it was: English, a language this doesn't
    know, or a sentence without a translation."""
    if text is None or lang not in LANGS:
        return text
    table = TEXT[lang]
    if text in table:
        return table[text]
    for word, local in LIGHT[lang].items():
        key = text.replace(word, "{light}")
        if key != text and key in table:
            return table[key].format(light=local)
    return text


def direction(code: str | None, lang: str) -> str | None:
    if code is None or lang not in LANGS:
        return code
    return DIRECTIONS[lang].get(code.strip().upper(), code)


def forecast(text: str | None, lang: str) -> str | None:
    if not text or lang not in LANGS:
        return text
    return FORECASTS[lang].get(text.strip().lower(), text)


_SPEED = re.compile(r"(\d+)(?: to (\d+))? mph", re.IGNORECASE)


def wind_speed(text: str | None, lang: str) -> str | None:
    """NWS's "10 mph" or "5 to 10 mph" as `lang` writes a speed, the same
    as the site's (frontend i18n/weather.ts): 时速 words in Chinese, 時速
    and 시속 before the number in Japanese and Korean. Anything else as NWS
    wrote it."""
    if not text or lang not in LANGS:
        return text
    m = _SPEED.fullmatch(text.strip())
    if not m:
        return text
    low, high = m.group(1), m.group(2)
    if lang == "zh":
        return f"{low}–{high} 英里/小时" if high else f"{low} 英里/小时"
    if lang == "es":
        return f"{low} a {high} mph" if high else f"{low} mph"
    if lang == "ko":
        return f"시속 {low}~{high}마일" if high else f"시속 {low}마일"
    return f"時速{low}〜{high}マイル" if high else f"時速{low}マイル"
