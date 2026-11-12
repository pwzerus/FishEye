"""繁體中文: the API's Simplified Chinese turned Traditional, with Taiwan's
words (knowledge/zh_hant.py), for requests in "zht" (api/zh_hant.py)."""

from __future__ import annotations

from types import SimpleNamespace

from app.knowledge import error_text, zh_hant
from app.services import password_reset

# Characters that only Simplified writes this way: none may be left.
SIMPLIFIED_ONLY = set("钓鱼获这们说饵鲶鲈鳟里发湖钩线们么张条")


def no_simplified(text: str) -> bool:
    return not (set(text) & SIMPLIFIED_ONLY)


def test_simplified_turns_traditional_with_taiwan_words():
    assert zh_hant.traditional("钓友渔获") == "釣友漁獲"
    assert zh_hant.traditional("密歇根州") == "密西根州"
    assert zh_hant.traditional("得克萨斯州") == "德克薩斯州"
    assert zh_hant.traditional("登录后可以评论") == "登入後可以評論"
    assert zh_hant.traditional("Largemouth Bass · 30.25, -97.72") == "Largemouth Bass · 30.25, -97.72"


def test_the_taiwan_words_that_dont_fit_a_fishing_site_are_put_back():
    assert zh_hant.traditional("你的渔获已发布") == "你的漁獲已發布"  # not 釋出, a software release
    assert zh_hant.traditional("由管理员审核") == "由管理員審核"  # not 稽核, an audit
    assert zh_hant.traditional("创建账户") == "建立帳戶"
    assert zh_hant.traditional("没有获得定位权限。") == "沒有獲得定位權限。"
    assert zh_hant.traditional("局部多云") == "局部多雲"
    assert zh_hant.traditional("最多只能缩小到这里") == "最多只能縮小到這裡"
    # Mainland words, in what Taiwan says.
    assert zh_hant.traditional("输入你的邮箱") == "輸入你的電子郵件"
    assert zh_hant.traditional("小浮漂和渔轮") == "小浮標和捲線器"


def test_a_question_in_traditional_is_read_in_the_guides_simplified():
    assert zh_hant.simplified("用什麼餌釣鯰魚？") == "用什么饵钓鲶鱼？"
    assert zh_hant.simplified("What bait?") == "What bait?"


def test_an_answer_says_its_text_is_traditional():
    answer = {"title": "钓鲶鱼", "lang": "zh", "body_lang": "zh", "text_lang": None, "url": "https://x.org/a", "n": 3}
    assert zh_hant.traditional_tree(answer) == {
        "title": "釣鯰魚", "lang": "zh-Hant", "body_lang": "zh-Hant", "text_lang": None, "url": "https://x.org/a", "n": 3,
    }


def test_guides_and_the_handbook_come_in_traditional(client):
    simplified = client.get("/api/species/guides?lang=zh").json()
    traditional = client.get("/api/species/guides?lang=zht").json()
    assert len(traditional) == len(simplified)
    bass = next(g for g in traditional if g["slug"] == "largemouth-bass")
    assert bass["text_lang"] == "zh-Hant"
    text = " ".join(bass["why_these_baits"] + bass["tips"])
    assert text and no_simplified(text), text[:200]
    assert bass["slug"] == "largemouth-bass"  # ids stay as they are

    topics = client.get("/api/species/handbook?lang=zht").json()
    written = [t for t in topics if t.get("body_lang")]
    assert written and all(t["body_lang"] == "zh-Hant" for t in written)
    assert no_simplified(" ".join(written[0]["body"]))


def test_simplified_and_english_are_left_alone(client):
    guides = client.get("/api/species/guides?lang=zh").json()
    assert next(g for g in guides if g["slug"] == "largemouth-bass")["text_lang"] == "zh"
    english = client.get("/api/species/guides").json()
    assert next(g for g in english if g["slug"] == "largemouth-bass")["text_lang"] in (None, "en")


def test_ask_in_traditional_finds_the_passage_and_answers_in_traditional(client):
    body = client.post("/api/ask", json={"question": "用什麼餌釣鯰魚？", "lang": "zht"}).json()
    assert body["answer_source"] == "passages", body
    assert any(c["id"].startswith("channel-catfish#") for c in body["citations"]), [c["id"] for c in body["citations"]]
    assert no_simplified(body["answer"]), body["answer"]


def test_taiwans_words_for_gear_are_fishing_questions(client):
    body = client.post("/api/ask", json={"question": "捲線器怎麼選？", "lang": "zht"}).json()
    assert body["trace"]["outcome"] != "off_topic", body
    body = client.post("/api/ask", json={"question": "浮標要用多大的？", "lang": "zht"}).json()
    assert body["trace"]["outcome"] != "off_topic", body


def test_the_size_limit_comes_first_for_a_request_in_traditional(client):
    """The middleware reads a JSON body to rewrite it, so it must only ever
    see bodies the size check has let through (it runs inside that check)."""
    from app.main import MAX_OTHER_BODY

    big = client.post(
        "/api/ask",
        content=b'{"question": "x", "lang": "zht"}',
        headers={"content-type": "application/json", "content-length": str(MAX_OTHER_BODY + 1)},
    )
    assert big.status_code == 413


def test_a_body_it_cannot_read_goes_on_as_it_came(client):
    broken = client.post("/api/ask", content=b'{"lang": "zht", "question": ', headers={"content-type": "application/json"})
    assert broken.status_code == 422  # the route's own refusal, not a crash here


def test_an_error_answer_comes_back_traditional_too(client):
    missing = client.get("/api/species/guides/no-such-fish?lang=zht")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")
    assert int(missing.headers["content-length"]) == len(missing.content)


def test_the_answers_length_matches_its_body(client):
    answer = client.get("/api/species/handbook?lang=zht")
    assert answer.status_code == 200
    assert int(answer.headers["content-length"]) == len(answer.content)


def test_a_refusal_is_said_in_traditional():
    assert error_text.tr("Email or password is incorrect.", "zht") == "電子郵件或密碼不正確。"
    assert error_text.tr("Email or password is incorrect.", "zh") == "邮箱或密码不正确。"


def test_the_reset_mail_is_written_in_traditional():
    user = SimpleNamespace(email="a@example.com", display_name="小王")
    mail = password_reset.mail_for(user, "https://fisheyefishing.com/reset-password?token=t", 2, "zht")  # type: ignore[arg-type]
    assert "密碼" in mail.subject and no_simplified(mail.subject + mail.text)
    assert "https://fisheyefishing.com/reset-password?token=t" in mail.text
