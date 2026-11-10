"""Questions about FishEye itself: "how do I share a catch", "is the photo check accurate".

The guides are about fishing, so these found nothing, or something that shared
a word with them. Ask says what the site does instead (replies.site_help), in
the asker's language. Patterns, because a wrong match here would answer a
fishing question with directions: each one names the thing on the site.
"""
from __future__ import annotations

import re

ABOUT = "about"
ACCOUNT = "account"
ALERTS = "alerts"
SHARE = "share"
PHOTO = "photo"
FIND = "find"
PRICE = "price"
MISSING_WATER = "missing_water"
PRIVACY = "privacy"
EDIT_CATCH = "edit_catch"
UPLOAD = "upload"
LANGUAGE = "language"
MAP_TROUBLE = "map_trouble"

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        ABOUT,
        re.compile(
            r"^(你是谁|你是什么|你是ai吗|你能做什么|你会什么|我能问什么|能问什么|这是什么网站)|(这个|这)\s*(网站|app|应用|软件).{0,3}(是)?(干什么|干嘛|做什么|能做什么)|(fisheye|这个网站|这个\s*app|这个应用).{0,4}怎么用|怎么用(这个网站|这个\s*app|fisheye)"
            r"|\b(who are you|what can you do|what is fisheye|what can i ask)\b",
            re.I,
        ),
    ),
    (
        ACCOUNT,
        re.compile(
            r"(怎么|如何|在哪).{0,4}(注册|登录|登陆|注销|改密码|修改密码|改名|改昵称)|忘记密码|忘了密码|密码忘了|删除账号|删除账户|注销账号|注销账户"
            r"|\b(sign up|create an account|forgot my password|reset my password|delete my account|change my password)\b",
            re.I,
        ),
    ),
    (
        ALERTS,
        re.compile(r"怎么订阅|如何订阅|订阅(提醒|鱼讯|邮件)|提醒我|通知我|邮件提醒|鱼讯提醒|\bsubscribe\b|\bnotify me\b|\bcatch alerts?\b|\be-?mail\b.{0,20}\b(alerts?|notif)", re.I),
    ),
    (
        SHARE,
        re.compile(
            r"(怎么|如何|怎样|在哪|哪里|能不能|可以).{0,8}(分享|发布|上传).{0,6}(渔获|鱼获|钓获|照片|战果|鱼)|分享渔获|分享不了|分享按钮"
            r"|\b(share|post|upload|add)\s+(?:(?:a|my|your|the|this)\s+)?(?:fish\s+)?catch(es)?\b",
            re.I,
        ),
    ),
    (
        PHOTO,
        re.compile(
            r"(拍照|拍张照|拍了|照片|图片|相机).{0,10}(识别|认鱼|认出|识鱼|认得|没有鱼|没找到鱼|不是鱼)|(识别|认鱼).{0,8}(准|靠谱|对不对)"
            r"|\bphoto (check|id)\b|\bidentify\b.{0,20}\b(photo|picture)\b|\b(photo|picture)\b.{0,30}\bidentify\b",
            re.I,
        ),
    ),
    (PRIVACY, re.compile(r"(渔获|钓点).{0,8}(私密|隐藏|公开|别人)|别人.{0,6}(看到|知道).{0,6}(钓点|渔获|位置)|私密|\b(private|hide)\b.{0,20}\b(catch|spot)\b|\bwho can see\b", re.I)),
    (EDIT_CATCH, re.compile(r"(删除|删掉|修改|编辑|改).{0,6}(渔获|鱼获|我发的)|\b(delete|edit|remove)\s+(?:(?:a|my|the|this)\s+)?catch\b", re.I)),
    (UPLOAD, re.compile(r"(照片|图片).{0,6}(传不上|上传失败|传不了|发不上)|\b(photo|picture)\b.{0,20}\b(won't|will not|can't|cannot|fails?)\b.{0,10}\bupload\b", re.I)),
    (LANGUAGE, re.compile(r"(换|改|切换).{0,3}(语言|中文|英文)|\b(change|switch)\b.{0,12}\blanguage\b", re.I)),
    (MAP_TROUBLE, re.compile(r"地图.{0,6}(打不开|加载不|不显示|空白|看不到)|\bmap\b.{0,20}\b(won't|will not|doesn't|does not|not)\b.{0,8}\b(load|open|show)\b", re.I)),
    (PRICE, re.compile(r"(网站|app|应用|软件|fisheye).{0,6}(收费|要钱|免费)|\b(is|does)\b.{0,20}\bfisheye\b.{0,12}\b(free|cost)\b", re.I)),
    (MISSING_WATER, re.compile(r"找不到.{0,8}(湖|水库|池塘)|地图上没有|\b(lake|pond|water)\b.{0,20}\b(missing|not on the map)\b", re.I)),
    (
        FIND,
        re.compile(
            r"(怎么|如何|在哪|哪里).{0,4}(找|看|查).{0,2}(附近|周围|周边).{0,3}(湖|钓点|水库|水域|池塘)|地图怎么用"
            r"|\bhow\b.{0,12}\bfind\b\s+(?:(?:a|an|the|some|nearby|local)\s+)*(?:lakes?|ponds?)\b",
            re.I,
        ),
    ),
)


def topic(question: str) -> str | None:
    """Which part of the site the question is about, if it is about the site."""
    for name, pattern in _PATTERNS:
        if pattern.search(question):
            return name
    return None
