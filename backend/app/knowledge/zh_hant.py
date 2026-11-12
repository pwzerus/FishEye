"""Traditional Chinese (Taiwan), made from FishEye's Simplified Chinese.

FishEye's Chinese is written once, in Simplified. The site's 繁體中文
(language "zht") is that Chinese in Traditional characters and Taiwan's
usual words: OpenCC's s2twp (Apache-2.0), then the few words that rule gets
wrong on a fishing site (FIXES). The site's own words are made the same way
ahead of time (frontend/scripts/zh_hant.py, same FIXES); the API's are made
as they go out (api/zh_hant.TraditionalChinese).
"""

from __future__ import annotations

import re
import threading
from functools import lru_cache
from typing import Any

import opencc

ZHT = "zht"
# How an answer in Traditional marks its text (lang, body_lang, text_lang…).
ZHT_TAG = "zh-Hant"

# Where the Taiwan rule picks a word this site doesn't mean. Keep in step
# with frontend/scripts/zh_hant.py.
FIXES: dict[str, str] = {
    "釋出": "發布",  # 发布: post a catch or a comment, not release software
    "稽核": "審核",  # 审核: moderators review a report; 稽核 is an audit
    "許可權": "權限",  # 定位权限: the location permission, as phones say it
    "區域性": "局部",  # 局部多云: forecasts in Taiwan say 局部 too
    "賬": "帳",  # 账户, 账号: 帳戶, 帳號 in Taiwan
    "隻能": "只能",  # 最多只能: "can only", read as the measure word 隻
    "隻有": "只有",
    # Mainland words Taiwan says otherwise, the rule keeps.
    "郵箱": "電子郵件",
    "反饋": "意見回饋",
    "浮漂": "浮標",  # what anglers in Taiwan call a bobber
    "漁輪": "捲線器",  # and a reel
    "得克薩斯": "德克薩斯",  # Texas, as Taiwan writes it; the other states come out right
    # The home-screen tip: the menus' own words on a phone set to Taiwan.
    "新增到主螢幕": "加入主畫面",
    "安裝應用”": "安裝應用程式”",
    "安卓": "Android",
    # Taiwan's quotation marks (after the fixes above, which match “”).
    "“": "「",
    "”": "」",
}

_HAN = re.compile(r"[㐀-鿿]")
_TO_TAIWAN = opencc.OpenCC("s2twp")
# Characters only, no Taiwan variants: tw2sp writes 鯰魚 as 鲇鱼, but the
# guides and Ask's words say 鲶鱼. Taiwan's own words for gear (卷线器,
# 浮标) are in Ask's Chinese words instead (services/rag/zh.py).
_TO_SIMPLIFIED = opencc.OpenCC("t2s")
# The converters are shared by the event loop and the worker threads.
_lock = threading.Lock()


@lru_cache(maxsize=50_000)
def traditional(text: str) -> str:
    """`text` in Traditional characters and Taiwan's words; text without
    Chinese comes back as it was."""
    if not _HAN.search(text):
        return text
    with _lock:
        out = _TO_TAIWAN.convert(text)
    for wrong, right in FIXES.items():
        out = out.replace(wrong, right)
    return out


def simplified(text: str) -> str:
    """A question typed in Traditional, in the Simplified Ask matches on."""
    if not _HAN.search(text):
        return text
    with _lock:
        return _TO_SIMPLIFIED.convert(text)


def _names_a_language(key: str) -> bool:
    return key == "lang" or key.endswith("_lang")


def traditional_tree(value: Any) -> Any:
    """A JSON answer with every string Traditional, and every "zh" that says
    what language a text is in turned "zh-Hant" (the page's lang attribute
    then picks Traditional glyphs)."""
    if isinstance(value, str):
        return traditional(value)
    if isinstance(value, list):
        return [traditional_tree(v) for v in value]
    if isinstance(value, dict):
        return {
            k: (ZHT_TAG if v == "zh" else v) if _names_a_language(k) else traditional_tree(v)
            for k, v in value.items()
        }
    return value
