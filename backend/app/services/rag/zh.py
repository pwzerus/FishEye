"""Chinese questions (docs/adr/0025).

The guides are English. The embedding model reads Chinese, but measured on
the eval it ranks the right English passage in its top four for only about
60% of Chinese questions, and its similarity scores can't tell a Chinese
fishing question from an off-topic one. So, like the English side, the
parts that decide something are rules that can be read and tested:

- `is_on_topic`: Chinese fishing words. "钓" alone covers most questions;
  "鱼" alone does not ("鱼香肉丝怎么做", "金鱼怎么养" are not fishing).
- `with_english`: a glossary that appends the English words the guides use,
  so keyword search can rank Chinese questions too ("剥皮" -> skin).
- `is_howto`: "鲈鱼怎么钓" with nothing more specific.

Fish names live with the English ones in retriever.ZH_SPECIES_ALIASES.
Chinese has no spaces, so everything here matches substrings, longest first.
"""
from __future__ import annotations

import re

CJK_RE = re.compile(r"[㐀-鿿]")

FISHING_TERMS = (
    "钓", "饵", "鱼钩", "渔轮", "鱼轮", "鱼竿", "钓竿", "鱼线", "浮漂", "浮子", "铅坠",
    "路亚", "亮片", "放流", "杀鱼", "放血", "去鳞", "刮鳞", "剥皮", "鱼片", "切鱼", "打窝",
    "鱼获", "咬钩", "上钩", "圈钩", "子线", "转环", "帕洛马结", "克林奇结", "鱼群", "产卵",
    "放养", "钩", "编织线", "尼龙线", "碳线", "子线",
    # A rod on its own ("几根竿": how many rods) and a catch limit; the
    # 2026-10-29 persona review asked Georgia's rod rule in Chinese and was
    # told it wasn't a fishing question.
    "竿", "限额",
    # The two reels by their usual names; "纺车轮怎么绕线" was turned away.
    "纺车轮", "水滴轮",
    # Added 2026-11-08: "卸力应该调多紧" (how tight a drag) was turned away.
    "卸力", "挂底", "抄网", "遛鱼",
)

# Chinese term -> the English words the guides use for it.
GLOSSARY: dict[str, str] = {
    "夏天": "summer", "夏季": "summer", "深水": "deep water", "水温": "water temperature",
    # Added 2026-11-06: salmon, steelhead and other cold-water fish; thermocline; senses.
    "硬头鳟": "steelhead rainbow trout",
    "钢头鳟": "steelhead rainbow trout",
    "奇努克鲑": "chinook king salmon",
    "国王鲑": "chinook king salmon",
    "帝王鲑": "chinook king salmon",
    "大鳞大麻哈鱼": "chinook king salmon",
    "银鲑": "coho silver salmon",
    "驼背大麻哈鱼": "pink salmon",
    "粉鲑": "pink salmon",
    "三文鱼": "salmon",
    "鲑鱼": "salmon",
    "大麻哈鱼": "salmon",
    "湖红点鲑": "lake trout",
    "湖鳟": "lake trout",
    "湖鲟": "lake sturgeon",
    "鲟鱼": "sturgeon",
    "江鳕": "burbot eelpout",
    "白鲑": "whitefish cisco",
    "胡瓜鱼": "smelt",
    "拖钓": "trolling troll",
    "冰钓": "ice fishing",
    "温跃层": "thermocline layers",
    "水温分层": "thermocline layers",
    "侧线": "lateral line vibration",
    "嗅觉": "smell scent",
    "鱼卵": "eggs spawn sac",
    "鱼籽": "eggs spawn sac",
    "洄游": "run spawn river",
    "溪流": "stream river",
    "河流": "river stream",
    "活饵": "live bait",
    "钓饵": "bait",
    "鱼饵": "bait",
    "拟饵": "lure lures",
    "假饵": "lure lures",
    "路亚": "lure lures",
    "软饵": "soft plastic worm jig",
    "硬饵": "crankbait",
    "复合亮片": "spinnerbait",
    "旋转亮片": "spinner",
    "亮片": "spoon spinner",
    "勺子": "spoon",
    "水面系": "topwater",
    "饵": "bait",
    "蚯蚓": "worm worms nightcrawler",
    "活小鱼": "live minnow minnows",
    "小活鱼": "live minnow minnows",
    "小鱼": "minnow minnows",
    "米诺": "minnow minnows",
    "蟋蟀": "cricket",
    "蚱蜢": "grasshopper",
    "昆虫": "insect insects",
    "小龙虾": "crayfish crawfish",
    "鸡肝": "chicken liver",
    "臭饵": "stink bait",
    "面团": "dough bait",
    "玉米": "corn",
    "虾": "shrimp",
    "纺车轮": "spinning reel",
    "水滴轮": "baitcasting reel",
    "封闭式": "spincast reel",
    "渔轮": "reel",
    "鱼轮": "reel",
    "鱼竿": "rod",
    "钓竿": "rod",
    "调性": "rod action",
    "编织线": "braid braided line",
    "尼龙线": "monofilament mono line",
    "碳线": "fluorocarbon line",
    "鱼线": "line",
    "圈钩": "circle hook",
    "钩号": "hook size",
    "鱼钩": "hook",
    "钩": "hook",
    "开口铅": "split shot",
    "铅坠": "sinker weight",
    "活动浮漂": "slip bobber",
    "浮漂": "bobber float",
    "浮子": "bobber float",
    "子线": "leader",
    "转环": "swivel",
    "帕洛马结": "palomar knot",
    "克林奇结": "improved clinch knot",
    "结": "knot",
    "绑鱼钩": "knot improved clinch palomar",
    "鱼钩怎么绑": "knot improved clinch palomar",
    "钩怎么绑": "knot improved clinch palomar",
    # Line onto the reel (the arbor knot), not a reel question. 上线 is also
    # "to go online", but the glossary only ranks: whether a question is
    # about fishing at all is is_on_topic's call, and 上线 isn't in it.
    "绑到渔轮": "arbor knot line reel spool",
    "绑在渔轮": "arbor knot line reel spool",
    "绑到轮上": "arbor knot line reel spool",
    "绕线": "arbor knot line reel spool",
    "上线": "arbor knot line spool",
    "线杯结": "arbor knot",
    "绑钩": "knot improved clinch palomar",
    "绑线": "line knot",
    "打结": "knot",
    "绑": "knot",
    "放流": "release",
    "保鲜": "keep fresh ice cooler",
    "冰": "ice",
    "杀鱼": "kill dispatch",
    "杀": "kill dispatch",
    "放血": "bleed",
    "去鳞": "scale scaling",
    "刮鳞": "scale scaling",
    "剥皮": "skin skinning",
    "切片": "fillet",
    "鱼片": "fillet",
    "清洗": "clean cleaning",
    "处理": "clean cleaning",
    "好吃": "eat table",
    "能吃": "eat table safe",
    "吃": "eat",
    "安全": "safe",
    "烹饪": "cook",
    "做菜": "cook",
    "温度": "temperature",
    "区别": "difference tell apart",
    "区分": "difference tell apart",
    "分辨": "difference tell apart",
    "长什么样": "look like identify",
    "特征": "identify",
    "胡须": "whiskers barbels",
    "尾巴": "tail",
    "方": "square",
    "栖息": "habitat live",
    "生活在": "live habitat",
    "在哪": "where",
    "哪里": "where",
    "成群": "school schools",
    "产卵": "spawn",
    "季节": "season",
    "早上": "morning",
    "清晨": "morning",
    "傍晚": "evening",
    "什么时候": "when",
    "一天中": "time of day morning evening",
    "一天": "time of day",
    "时间": "time",
    "放养": "stock stocking",
    "为什么": "why",
    "好处": "advantage",
    "优点": "advantage",
    "挂": "hook",
    "小孩": "kid kids",
    "孩子": "kid kids",
    # Added 2026-11-08: the beginner questions (bites, landing, snags, line
    # twist, manners, weather and falling in).
    "伤到鱼": "unharmed without hurting",
    "伤鱼": "unharmed without hurting",
    "需要执照": "need a fishing license",
    "要执照": "need a fishing license",
    "需要钓鱼证": "need a fishing license",
    "卸力": "drag",
    "挂底": "snagged snag free hook",
    "打卷": "line twist loops tangle",
    "缠线": "line twist tangle",
    "咬钩": "bite set the hook",
    "咬口": "bite",
    "没口": "no bites nothing caught what to change",
    "不咬钩": "no bites nothing caught what to change",
    "没有口": "no bites nothing caught what to change",
    "一口都没有": "no bites nothing caught what to change",
    "提竿": "set the hook bite",
    "刺鱼": "set the hook",
    "遛鱼": "playing landing fish drag",
    "抄网": "landing net",
    "抄鱼": "landing net",
    "跑鱼": "lost fish landing",
    "脱钩": "fish came off landing",
    "偷饵": "bait disappearing nothing on the hook",
    "饵被吃": "bait disappearing nothing on the hook",
    "打雷": "thunder lightning",
    "雷电": "lightning",
    "闪电": "lightning",
    "雷雨": "thunderstorms lightning",
    "中暑": "heat stroke exhaustion",
    "高温": "heat",
    "落水": "falling into cold water",
    "冷水": "cold water",
    "失温": "hypothermia cold water",
    "礼仪": "manners sharing the water",
    "素质": "manners sharing the water",
    "儿童": "kid kids",
    "带娃": "kid kids taking kids fishing",
    # Added 2026-11-08 (gear care, new line, hook injuries, black spots, lead,
    # stocked trout). "放流" alone stays "release" ("放流的时候" is letting a
    # fish go); "放流的虹鳟" are stocked trout.
    "保养": "care clean store",
    "换线": "change new line",
    "换一次": "change how often",
    "多久换": "how often change",
    "扎到手": "hook in skin finger",
    "扎手": "hook in skin finger",
    "扎进": "hook in skin",
    "黑点": "black spots",
    "放流的虹鳟": "stocked rainbow trout",
    "放流的鳟鱼": "stocked trout",
    "放流虹鳟": "stocked rainbow trout",
    "放养的": "stocked",
    "投放的": "stocked",
    "出不了线": "line won't go out",
    "按钮式": "push-button spincast",
    "德州": "texas",
    "德克萨斯": "texas",
    "佐治亚": "georgia",
    "加州": "california",
    "加利福尼亚": "california",
    "乔治亚": "georgia",
    "钓鱼证": "fishing licence license",
    "执照": "licence license",
    "许可证": "licence license",
    "救生衣": "life jacket",
    "竿": "rod",
    "带走": "keep",
    "限额": "limit limits",
    "几条": "limit",
    "尺寸": "size length",
    "规定": "rules",
}
_GLOSSARY = sorted(GLOSSARY.items(), key=lambda kv: -len(kv[0]))

# What's left of "鲈鱼怎么钓啊？" once the fish's name is removed: if only
# these remain, the question is "how do I fish for it", nothing narrower.
_HOWTO_FILLER = (
    "请问", "怎么样", "怎么", "如何", "怎样", "钓法", "技巧", "方法", "钓鱼", "钓", "抓", "去",
    "我", "想", "要", "能", "才", "好", "的", "呢", "吗", "啊", "呀", "一下", "教", "新手",
)
_HOWTO_INTENT = ("钓", "抓")
_PUNCT_RE = re.compile(r"[\s\W_]+")


def has_chinese(text: str) -> bool:
    return bool(CJK_RE.search(text))


# "鱼" (fish) on its own is not a fishing question: 金鱼 is a goldfish, 鱼香
# is a flavour, 鱼缸 a tank. These are blanked out first, and then "鱼" counts
# like an English AMBIGUOUS_TERM — two of these words are needed, so
# "怎么给鱼保鲜" (how do I keep a fish fresh) is a fishing question and
# "鱼香肉丝怎么做" is not (docs/adr/0026).
NOT_FISHING = (
    "鱼香", "金鱼", "观赏鱼", "鱼缸", "水族", "鱼丸", "鱼干", "鱼翅", "鱼子酱", "木鱼",
    "鱿鱼", "章鱼", "鲍鱼", "鱼露", "鱼肝油", "鱼尾纹", "美人鱼", "鱼雷",
    "旗竿", "竹竿", "晾衣竿",
)
AMBIGUOUS_TERMS = (
    "鱼", "保鲜", "冷冻", "冷藏", "解冻", "清洗", "处理", "新鲜", "好吃", "能吃", "可以吃",
    "煮", "烤", "炸", "煎", "冰", "水", "湖", "河", "池塘", "水库", "天气", "风", "下雨",
    "季节", "早上", "清晨", "傍晚", "晚上", "什么时候", "刀", "肉质", "刺", "杀", "鳞", "腥",
    # Rules words: with a fish, a question about what may be kept.
    "带走", "执照", "几条", "规定", "尺寸",
)


def is_on_topic(text: str) -> bool:
    # The other meanings go first: 旗竿 (a flagpole) holds 竿, a rod.
    for word in NOT_FISHING:
        text = text.replace(word, "")
    if any(term in text for term in FISHING_TERMS):
        return True
    return sum(1 for term in AMBIGUOUS_TERMS if term in text) >= 2


def with_english(text: str) -> str:
    """`text` with the glossary's English for every Chinese term in it."""
    if not has_chinese(text):
        return text
    masked, words = text, []
    for term, english in _GLOSSARY:
        if term in masked:
            words.append(english)
            masked = masked.replace(term, " ")
    return f"{text} {' '.join(words)}"


def is_howto(residual: str) -> bool:
    if not any(w in residual for w in _HOWTO_INTENT):
        return False
    rest = residual
    for filler in sorted(_HOWTO_FILLER, key=len, reverse=True):
        rest = rest.replace(filler, "")
    return not _PUNCT_RE.sub("", rest)
