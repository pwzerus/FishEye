"""What Ask says in its own words, in the asker's language (en, zh, es, ko, ja).

The guides it quotes are English. Its own sentences (the line before the
passages, and the three kinds of "not covered", docs/adr/0026) are in the
language of the question: Chinese for a Chinese question, Spanish, Korean
or Japanese for one in those; for an English question, the site's language
(someone reading the site in Spanish can still type "crappie bait").
Japanese is told apart from Chinese by its kana, so it is asked first.
"""
from __future__ import annotations

from app.knowledge import jurisdictions
from app.knowledge.species_guides import GUIDES
from app.services.rag import es, ja, ko
from app.services.rag.zh import has_chinese

LANGS = ("en", "zh", "es", "ko", "ja")

# "No guide for that fish" when the fish's name can't be read back.
THAT_FISH = {"en": "that fish", "zh": "这种鱼", "es": "ese pez", "ko": "그 물고기", "ja": "その魚"}

# Spanish names of the states whose name differs from the English one.
ES_STATE_NAMES = {
    "DC": "Distrito de Columbia", "HI": "Hawái", "LA": "Luisiana", "MI": "Míchigan", "MS": "Misisipi",
    "MO": "Misuri", "NH": "Nuevo Hampshire", "NJ": "Nueva Jersey", "NM": "Nuevo México", "NY": "Nueva York",
    "NC": "Carolina del Norte", "ND": "Dakota del Norte", "OR": "Oregón", "PA": "Pensilvania",
    "SC": "Carolina del Sur", "SD": "Dakota del Sur", "WV": "Virginia Occidental",
}


def reply_lang(question: str, site_lang: str | None) -> str:
    if ja.is_japanese(question):
        return "ja"
    if ko.is_korean(question):
        return "ko"
    if has_chinese(question):
        return "zh"
    if es.is_spanish(question):
        return "es"
    return site_lang if site_lang in LANGS else "en"


def _state_name(code: str, lang: str) -> str:
    j = jurisdictions.JURISDICTIONS[code]
    if lang == "zh":
        return jurisdictions.ZH_STATE_NAMES.get(code, j.name)
    if lang == "es":
        return ES_STATE_NAMES.get(code, j.name)
    if lang == "ko":
        return ko.STATE_NAMES.get(code, j.name)
    if lang == "ja":
        return ja.STATE_NAMES.get(code, j.name)
    return j.name


def _states(n: int, dc: bool, lang: str) -> str:
    if lang == "zh":
        return f"{n}个州" + ("和华盛顿特区" if dc else "")
    if lang == "ja":
        return f"{n}州" + ("とワシントンD.C." if dc else "")
    if lang == "ko":
        return f"{n}개 주" + ("와 워싱턴 D.C." if dc else "")
    if lang == "es":
        return f"{n} estados" + (" y Washington D. C." if dc else "")
    return f"{n} states" + (" and Washington, D.C." if dc else "")


def _licensed(lang: str) -> str:
    return _states(*jurisdictions.license_count(), lang)


def _covered(lang: str) -> str:
    names = [_state_name(c.code, lang) for c in jurisdictions.covered()]
    if len(names) > 5:  # how many, not a list of forty names
        return _states(*jurisdictions.covered_count(), lang)
    if lang in ("zh", "ja"):
        return "、".join(names)
    if lang == "ko":
        return ", ".join(names)
    if lang == "es":
        return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"
    return jurisdictions.covered_names()


def _rules_written(lang: str) -> str:
    """Bait and license rules are written for different states, so "each"
    when the counts match, and not one number for both."""
    bait, lic = _covered(lang), _licensed(lang)
    same = bait == lic
    if lang == "ko":
        return f"지금까지 미끼 규정과 면허 규정은 각각 {bait}까지" if same else f"지금까지 미끼 규정은 {bait}, 면허 규정은 {lic}까지"
    if lang == "ja":
        return f"今のところ、エサとライセンスの規則はそれぞれ{bait}の分" if same else f"今のところ、エサの規則は{bait}、ライセンスの規則は{lic}の分"
    if lang == "zh":
        return f"饵料规定和执照规定目前各整理了{bait}" if same else f"目前整理了{bait}的饵料规定和{lic}的执照规定"
    if lang == "es":
        return f"Por ahora hay reglas de carnada y de licencia de {bait}, cada una" if same else f"Por ahora hay reglas de carnada de {bait} y de licencia de {lic}"
    return f"Bait rules and license rules are each written for {bait} so far" if same else f"Bait rules are written for {bait} so far and license rules for {lic}"


def coverage(lang: str) -> str:
    fish = len(GUIDES)
    rules = _rules_written(lang)
    if lang == "ko":
        return (
            f"FishEye에는 민물고기 {fish}종의 가이드(대부분 미국 전역에 사는 어종으로, 먹이, 사는 곳, 잘 먹히는 미끼와 "
            "그 이유, 낚싯대와 릴 구성, 손질과 요리법)와, 미끼, 루어, 장비, 매듭, 캐스팅, 날씨와 물, 안전, 잡은 "
            f"물고기 다루기에 대한 핸드북이 있어요. {rules} 정리했고, 물고기가 사는 곳의 예시는 텍사스주 것이 많아요. 둘 다 주마다 달라요."
        )
    if lang == "ja":
        return (
            f"FishEyeには、淡水魚{fish}種のガイド（多くは全米にいる魚で、何を食べ、どこにいるか、効くエサとその理由、"
            "竿とリールの組み合わせ、さばき方と料理）と、エサ、ルアー、道具、結び方、投げ方、天気と水、安全、"
            f"釣った魚の扱いについてのハンドブックがあります。{rules}を掲載していて、"
            "魚の生息場所の例にはテキサス州のものが多くあります。どちらも州によって違います。"
        )
    if lang == "zh":
        return (
            f"FishEye 目前收录了 {fish} 种淡水鱼的指南，其中大多数鱼在全美都有分布，内容包括食性、栖息地、有效的饵及原因、"
            "竿轮搭配，以及处理和烹饪方法。另有一本手册，介绍饵料、拟饵、装备、绳结、抛投、天气水情、安全和渔获处理。"
            f"{rules}；栖息地的举例多来自得克萨斯州。规定和栖息地都因州而异。"
        )
    if lang == "es":
        return (
            f"FishEye tiene guías de {fish} peces de agua dulce, casi todos presentes en todo EE. UU. (qué "
            "comen, dónde viven, qué carnadas funcionan y por qué, equipos de caña y carrete, y cómo limpiarlos "
            "y cocinarlos), y un manual sobre carnadas, señuelos, equipo, nudos, lances, clima y agua, seguridad "
            f"y cuidado de tu captura. {rules}, y muchos ejemplos de dónde viven los peces son de Texas; ambas cosas cambian según el estado."
        )
    return (
        f"FishEye covers {fish} freshwater fish, most of them found across the U.S. (what each one "
        "eats, where it lives, which baits work and why, rod-and-reel setups, and how to clean and "
        "cook it) plus a handbook on baits, lures, tackle, knots, casting, weather and water, safety "
        f"and caring for your catch. {rules}, and many examples of where fish live are Texas's; both differ by state."
    )


# When every passage shown is one the question library has in Chinese.
PASSAGES_INTRO_ZH_ORIGINAL = "以下是 FishEye 中的相关内容："


def passages_intro(lang: str) -> str:
    if lang == "zh":
        return "以下是 FishEye 指南中的相关内容（原文为英文）："
    if lang == "es":
        return "Esto es lo que dicen las guías de FishEye (en inglés):"
    if lang == "ko":
        return "FishEye 가이드에는 이렇게 나와 있어요(원문은 영어예요):"
    if lang == "ja":
        return "FishEyeのガイドには、こう書かれています（原文は英語）："
    return "Here's what the FishEye guides say:"


def no_match(lang: str) -> str:
    if lang == "zh":
        return f"FishEye 的指南尚未涉及这个问题。{coverage(lang)}你可以就这些方面提问。"
    if lang == "es":
        return f"Las guías de FishEye todavía no cubren eso. {coverage(lang)} Prueba preguntar sobre algo de eso."
    if lang == "ko":
        return f"FishEye 가이드에는 아직 그 내용이 없어요. {coverage(lang)} 이 중에서 물어봐 주세요."
    if lang == "ja":
        return f"FishEyeのガイドには、まだその内容がありません。{coverage(lang)}このどれかについて聞いてみてください。"
    return f"The FishEye guides don't cover that yet. {coverage(lang)} Try asking about one of those."


def no_lake(name: str, lang: str) -> str:
    if lang == "zh":
        return f"FishEye 没有名为“{name}”的湖泊记录。请检查拼写，或在地图上搜索。"
    if lang == "es":
        return f"FishEye no tiene registrado ningún lago llamado {name}. Revisa cómo se escribe o búscalo en el mapa."
    if lang == "ko":
        return f"FishEye에는 {name}(이)라는 호수 기록이 없어요. 철자를 확인하거나 지도에서 검색해 보세요."
    if lang == "ja":
        return f"FishEyeには{name}という湖の記録がありません。つづりを確認するか、地図で検索してください。"
    return f"FishEye has no lake called {name} on record. Check the spelling, or search for it on the map."


def use_the_map(lang: str) -> str:
    if lang == "zh":
        return "附近的钓点请在地图上查看：打开顶部的“找钓点”，点击“使用我的位置”或搜索城市名，即可看到周边的湖泊及其中的鱼种。"
    if lang == "es":
        return "Para saber dónde pescar cerca de ti, usa el mapa: abre «Dónde pescar», usa tu ubicación o busca una ciudad y verás los lagos de la zona y sus peces."
    if lang == "ko":
        return "주변 낚시터는 지도에서 확인하세요. 위쪽의 ‘낚시터 찾기’를 열고 내 위치를 쓰거나 도시를 검색하면 근처 호수와 어종이 나옵니다."
    if lang == "ja":
        return "近くの釣り場は地図で確認できます。上の「釣り場を探す」を開き、現在地を使うか都市名を検索すると、周辺の湖とそこにいる魚が表示されます。"
    return "For water near you, use the map: open Find water, use your location or search a city, and you'll see the lakes around you and what fish are in them."


_SITE_HELP = {
    "about": {
        "zh": "我是 FishEye 的问答搜索，根据 FishEye 的鱼类指南和手册回答钓鱼问题，例如用什么饵、如何绑钩、何时出钓、是否需要执照，以及渔获如何处理。答案均出自这些资料，出处标注在下方。",
        "en": "I'm FishEye's Ask search. I answer fishing questions from FishEye's fish guides and handbook: what bait to use, how to tie a hook on, when to go, whether you need a license, what to do with your catch. Every answer comes from those pages, and they're linked under it.",
        "es": "Soy la búsqueda de FishEye. Respondo preguntas de pesca con las guías de peces y el manual de FishEye: qué carnada usar, cómo atar un anzuelo, cuándo ir, si necesitas licencia, qué hacer con tu captura. Cada respuesta sale de esas páginas, y están enlazadas debajo.",
        "ko": "저는 FishEye의 질문 검색이에요. FishEye의 어종 가이드와 핸드북으로 낚시 질문에 답해요. 어떤 미끼를 쓸지, 바늘을 어떻게 묶는지, 언제 가면 좋은지, 면허가 필요한지, 잡은 물고기를 어떻게 하는지 물어보세요. 답은 모두 그 자료에서 나오고 아래에 출처가 있어요.",
        "ja": "FishEyeの質問検索です。FishEyeの魚ガイドとハンドブックをもとに、エサ、針の結び方、いつ行くか、ライセンスが必要か、釣った魚の扱いなど、釣りの質問に答えます。答えはすべてそれらのページからで、下に出典があります。",
    },
    "account": {
        "zh": "点击右上角即可登录或创建账户，也可以使用 Google 登录。如果忘记密码，请在登录页点击“忘记密码？”。登录后，可以在账户页修改名称和密码，或删除账户。",
        "en": "Use Sign in at the top right to sign in or create an account, or continue with Google. If you've forgotten your password, use Forgot password on the sign-in page. Your account page is where you change your name or password, or delete the account.",
        "es": "Usa Iniciar sesión, arriba a la derecha, para entrar o crear una cuenta, o continúa con Google. Si olvidaste la contraseña, usa la opción de la página de inicio de sesión. En tu cuenta puedes cambiar el nombre o la contraseña, o eliminarla.",
        "ko": "오른쪽 위에서 로그인하거나 계정을 만들 수 있고, Google로도 로그인할 수 있어요. 비밀번호를 잊었다면 로그인 페이지에서 찾을 수 있어요. 계정 페이지에서 이름과 비밀번호를 바꾸거나 계정을 삭제할 수 있어요.",
        "ja": "右上からログインまたはアカウント作成ができ、Googleでもログインできます。パスワードを忘れた場合はログインページから再設定できます。アカウントページで名前やパスワードの変更、アカウントの削除ができます。",
    },
    "alerts": {
        "zh": "登录后，在账户页打开“鱼讯提醒”，选择鱼种、地点和半径（英里）。半径范围内有人分享这种鱼且照片核对通过时，FishEye 会发邮件通知你，每封邮件都附有退订链接。",
        "en": "Sign in and open Catch alerts on your account page: pick a fish, a place and a radius in miles. When someone shares that fish inside the radius and the photo check backs it, FishEye emails you. Every email has an unsubscribe link.",
        "es": "Inicia sesión y abre Alertas de capturas en tu cuenta: elige un pez, un lugar y un radio en millas. Cuando alguien comparta ese pez dentro del radio y la foto lo confirme, FishEye te enviará un correo. Cada correo trae un enlace para cancelar.",
        "ko": "로그인한 뒤 계정 페이지의 조과 알림에서 어종, 장소, 반경(마일)을 고르세요. 반경 안에서 누군가 그 물고기를 공유하고 사진 확인을 통과하면 FishEye가 이메일을 보내요. 모든 메일에 수신 거부 링크가 있어요.",
        "ja": "ログインしてアカウントページの釣果アラートで、魚、場所、半径（マイル）を選びます。半径内で誰かがその魚を投稿し、写真の確認を通ると、FishEyeからメールが届きます。どのメールにも配信停止リンクがあります。",
    },
    "share": {
        "zh": "分享渔获分三步：打开“找钓点”，点击“分享渔获”（需先登录）；在地图上点选你钓鱼的水域；上传一张鱼的照片，系统会自动填写鱼种。每次只分享一条鱼，照片中也只拍这一条。标记必须放在地图上已命名的湖泊、河流或池塘上，否则按钮显示为灰色，并在旁边注明原因。",
        "en": "Sharing a catch takes three steps: open Find water and press Share a catch (sign in first), tap the water you fished on the map, then add a photo of the fish and FishEye fills in the species. One fish per share, and only that fish in the photo. The pin has to be on a lake, river or pond the map names; otherwise the button stays grey and says why.",
        "es": "Compartir una captura son tres pasos: abre Dónde pescar y pulsa Compartir una captura (inicia sesión antes), toca en el mapa el agua donde pescaste y añade una foto del pez; FishEye rellena la especie. Un pez por vez, y solo ese pez en la foto. El marcador debe estar en un lago, río o estanque con nombre en el mapa; si no, el botón queda gris y explica por qué.",
        "ko": "조과 공유는 세 단계예요. 낚시터 찾기를 열고 조과 공유를 누른 뒤(먼저 로그인), 지도에서 낚시한 물을 누르고 물고기 사진을 올리면 어종이 자동으로 채워져요. 한 번에 한 마리, 사진에도 그 물고기만 나오게 해 주세요. 표시는 지도에 이름이 있는 호수, 강, 연못 위에 있어야 하고, 아니면 버튼이 회색이 되고 이유가 표시돼요.",
        "ja": "釣果の投稿は3ステップです。釣り場を探すを開いて釣果を投稿を押し（先にログイン）、地図で釣った水面を押して、魚の写真を追加すると魚種が自動で入ります。1回に1匹、写真にもその魚だけが写るようにしてください。印は地図に名前のある湖、川、池の上に置きます。そうでないとボタンは灰色のままで、理由が表示されます。",
    },
    "privacy": {
        "zh": "分享渔获时可以选择“仅自己”，只有你能看到。选择“公开”时，其他人默认只能看到所在的湖或河，看不到确切钓点；如果希望公开确切位置，需要勾选“让其他钓友看到确切钓点”。照片中的位置信息会在保存前删除。",
        "en": "When you share a catch you can choose Only me, and nobody else sees it. A public catch shows others only which lake or river it's on, not the spot, unless you tick the box to show the exact spot. Location data in a photo is removed before it's saved.",
    },
    "edit_catch": {
        "zh": "打开“渔获”，切换到“我的”，点开对应的渔获，即可修改、增删照片或删除。删除后无法恢复。",
        "en": "Open Catches, switch to Mine and open the catch: you can edit it, add or remove photos, or delete it. A deleted catch can't be brought back.",
    },
    "upload": {
        "zh": "照片须为 JPG、PNG 或 WebP 格式，单张不超过 10 MB。如果仍无法上传，通常是网络中断所致，请换到信号较好的地方重试；如问题依旧，可在首页或头像菜单中点击“发送反馈”告诉我们。",
        "en": "Photos need to be JPG, PNG or WebP, up to 10 MB each. If one still won't go up, it's usually the connection: try again with a better signal, or use Send feedback on the home page or in your account menu.",
    },
    "language": {
        "zh": "点击右上角的地球图标即可切换语言：中文、English、Español、한국어、日本語。",
        "en": "Use the globe at the top right to switch language: English, Chinese, Spanish, Korean or Japanese.",
    },
    "map_trouble": {
        "zh": "地图需要联网使用。请先刷新页面，或换到信号较好的地方重试；如仍无法打开，可在首页或头像菜单中点击“发送反馈”告诉我们。",
        "en": "The map needs a connection. Refresh the page or try where the signal is better; if it still won't open, use Send feedback on the home page or in your account menu.",
    },
    "price": {
        "zh": "FishEye 目前免费：地图、鱼类指南、手册和问答均不收费，注册账户也免费。",
        "en": "FishEye is free to use: the map, the fish guides, the handbook and Ask, and an account costs nothing.",
        "es": "FishEye es gratis: el mapa, las guías de peces, el manual y las preguntas, y crear una cuenta tampoco cuesta nada.",
        "ko": "FishEye는 무료예요. 지도, 어종 가이드, 핸드북, 질문하기 모두 무료이고 계정 만들기도 무료예요.",
        "ja": "FishEyeは無料です。地図、魚ガイド、ハンドブック、質問はすべて無料で、アカウント作成も無料です。",
    },
    "missing_water": {
        "zh": "如果地图上找不到你常去的水域，可以在地图上点选该位置，再点击“地图上缺少这片水域？告诉我们”提交，我们核对后会添加。也可以先搜索城市名，放大地图确认它是否使用了其他名称。",
        "en": "If water you fish isn't on the map, tap the spot and use \"Water not on the map? Tell us\", and it gets checked and added. Searching a nearby town and zooming in also helps: it may be there under another name.",
        "es": "Si el agua donde pescas no está en el mapa, toca el lugar y usa la opción para avisarnos; la revisaremos y la añadiremos. También puedes buscar un pueblo cercano y acercar el mapa: puede estar con otro nombre.",
        "ko": "자주 가는 물이 지도에 없으면 그 위치를 누르고 지도에 없는 물을 알려 주세요. 확인한 뒤 추가해요. 근처 도시를 검색해 확대해 보면 다른 이름으로 있을 수도 있어요.",
        "ja": "よく行く水域が地図にない場合は、その場所を押して地図にない水域を知らせてください。確認して追加します。近くの町を検索して拡大すると、別の名前で載っていることもあります。",
    },
    "photo": {
        "zh": "拍照识鱼时，每张照片只拍一条鱼，拍下整条鱼的侧面，并保证光线充足，这样识别最准确。多条鱼同框、鱼太小或光线太暗时容易出错；外形相似的鱼（例如几种黑鲈）有时只能识别到大类。照片中没有鱼时，系统会直接提示。识别结果仅供参考，是否留鱼以你所在州的规定为准。",
        "en": "The photo check is most accurate with one fish in the photo, its whole side showing, in good light. Several fish together, a very small fish or a dark photo can fool it, and look-alikes (the black basses, say) sometimes only get as far as the group. A photo with no fish in it is told so. Treat the answer as a guide: what you may keep is up to your state's rules.",
        "es": "La revisión por foto acierta más con un solo pez en la foto, de costado y completo, con buena luz. Varios peces juntos, un pez muy pequeño o una foto oscura pueden confundirla, y los parecidos (como las lobinas) a veces solo llegan al grupo. Si la foto no muestra ningún pez, te lo dice. Tómalo como orientación: lo que puedes quedarte depende de las reglas de tu estado.",
        "ko": "사진 확인은 사진에 물고기 한 마리만, 옆모습 전체가 밝게 나올 때 가장 정확해요. 여러 마리가 함께 있거나, 너무 작거나 어두우면 틀릴 수 있고, 닮은 어종은 무리까지만 알아볼 때도 있어요. 물고기가 없는 사진은 없다고 알려 줘요. 참고로만 쓰고, 가져갈 수 있는지는 주 규정을 따르세요.",
        "ja": "写真の確認は、1枚に1匹、魚の側面全体が明るく写っているときが最も正確です。何匹も一緒だったり、とても小さかったり、暗かったりすると間違えることがあり、似た魚は仲間までしかわからないこともあります。魚が写っていない写真にはそう伝えます。結果は目安にして、持ち帰れるかは州の規則に従ってください。",
    },
}


def site_help(topic: str, lang: str) -> str:
    """What the site does, when the question is about the site (site_help.py)."""
    if topic == "find":
        return use_the_map(lang)
    words = _SITE_HELP[topic]
    return words.get(lang, words["en"])


def off_topic(lang: str) -> str:
    if lang == "zh":
        return f"这似乎不是钓鱼问题，或者我没有理解你的意思。{coverage(lang)}请在问题中提到具体的鱼、饵或装备，可以用中文、英文、西班牙语、韩语或日语提问。"
    if lang == "es":
        return (
            f"Eso no parece una pregunta de pesca, o no la entendí. {coverage(lang)} Prueba nombrar un pez, "
            "una carnada o un equipo, en español, inglés, chino, coreano o japonés."
        )
    if lang == "ko":
        return (
            f"낚시 질문이 아닌 것 같아요. 아니면 제가 잘 이해하지 못했어요. {coverage(lang)} 어종, 미끼, 장비 이름을 "
            "넣어서 한국어, 영어, 중국어, 스페인어, 일본어로 물어보세요."
        )
    if lang == "ja":
        return (
            f"釣りの質問ではないようです。あるいは、うまく理解できませんでした。{coverage(lang)}魚、エサ、道具の名前を"
            "入れて、日本語、英語、中国語、スペイン語、韓国語で質問してください。"
        )
    return (
        "That doesn't look like a fishing question to me — or I didn't understand it. "
        f"{coverage(lang)} Try naming a fish, a bait or a piece of tackle, in English, Chinese, Spanish, Korean or Japanese."
    )


def unguided_fish(name: str, lang: str) -> str:
    if lang == "zh":
        return f"FishEye 尚未收录{name}的指南，目前只能给出推测性的回答。{coverage(lang)}"
    if lang == "es":
        return f"FishEye todavía no tiene guía para {name}, así que cualquier cosa sobre ese pez sería adivinar. {coverage(lang)}"
    if lang == "ko":
        return f"FishEye에는 아직 {name} 가이드가 없어서, 그 물고기에 대해 답하면 짐작일 뿐이에요. {coverage(lang)}"
    if lang == "ja":
        return f"FishEyeにはまだ{name}のガイドがないので、その魚について答えても推測になってしまいます。{coverage(lang)}"
    return f"FishEye has no guide for {name} yet, so anything it told you about that fish would be guesswork. {coverage(lang)}"


def other_state(state: str, lang: str) -> str:
    if lang == "zh":
        return jurisdictions.other_state_answer_zh(state)
    if lang == "ko":
        return _other_state_ko(state)
    if lang == "ja":
        return _other_state_ja(state)
    if lang != "es":
        return jurisdictions.other_state_answer(state)
    j = jurisdictions.JURISDICTIONS[state]
    name = _state_name(state, lang)
    agency = j.agency_short or f"la agencia de pesca y vida silvestre de {name}"
    if j.covered:
        return (
            f"FishEye ya escribió algunas reglas de pesca de {name}, pero no la de esta pregunta. Revisa las "
            f"reglas vigentes con {agency} antes de pescar. Todo lo de cómo pescar, manejar y cocinar un pez "
            "funciona igual en cualquier lugar."
        )
    return (
        f"Esa es una pregunta sobre las reglas de pesca de {name}, y FishEye todavía no las ha escrito (por ahora "
        f"revisó las reglas de {_covered(lang)}). Las reglas de licencias, límites, carnada y lanchas cambian de un "
        f"estado a otro, así que revisa las vigentes con {agency}. Todo lo de cómo pescar, manejar y cocinar un pez "
        "funciona igual en cualquier lugar."
    )


def _other_state_ko(state: str) -> str:
    j = jurisdictions.JURISDICTIONS[state]
    name = _state_name(state, "ko")
    agency = j.agency_short or f"{name} 어류·야생동물 기관"
    same = "물고기를 잡고 다루고 요리하는 방법은 어디서나 똑같아요."
    if j.covered:
        return (
            f"FishEye에 {name}의 낚시 규정이 일부 정리되어 있지만, 이 질문에 해당하는 규정은 아직 없어요. "
            f"낚시하기 전에 {agency}에서 최신 규정을 확인하세요. {same}"
        )
    return (
        f"{name}의 낚시 규정에 대한 질문인데, FishEye는 아직 그 규정을 정리하지 않았어요(지금까지 "
        f"{_covered('ko')}의 규정을 확인했어요). 면허, 한도, 미끼, 보트 규정은 주마다 다르니 {agency}에서 "
        f"최신 규정을 확인하세요. {same}"
    )


def _other_state_ja(state: str) -> str:
    j = jurisdictions.JURISDICTIONS[state]
    name = _state_name(state, "ja")
    agency = j.agency_short or f"{name}の魚類野生生物局"
    same = "魚の釣り方、扱い方、料理の仕方は、どこでも同じです。"
    if j.covered:
        return (
            f"FishEyeは{name}の釣りの規則をいくつか掲載していますが、この質問の規則はまだありません。"
            f"釣りをする前に、{agency}で最新の規則を確認してください。{same}"
        )
    return (
        f"これは{name}の釣りの規則についての質問ですが、FishEyeはまだ掲載していません（今のところ"
        f"{_covered('ja')}の規則を確認済みです）。ライセンス、制限、エサ、ボートの規則は州ごとに違うので、"
        f"{agency}で最新の規則を確認してください。{same}"
    )
