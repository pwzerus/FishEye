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
)

# Chinese term -> the English words the guides use for it.
GLOSSARY: dict[str, str] = {
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
)
AMBIGUOUS_TERMS = (
    "鱼", "保鲜", "冷冻", "冷藏", "解冻", "清洗", "处理", "新鲜", "好吃", "能吃", "可以吃",
    "煮", "烤", "炸", "煎", "冰", "水", "湖", "河", "池塘", "水库", "天气", "风", "下雨",
    "季节", "早上", "清晨", "傍晚", "晚上", "什么时候", "刀", "肉质", "刺", "杀", "鳞", "腥",
)


def is_on_topic(text: str) -> bool:
    if any(term in text for term in FISHING_TERMS):
        return True
    for word in NOT_FISHING:
        text = text.replace(word, "")
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
