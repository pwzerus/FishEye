"""The API's messages to people in the site's other languages (ADR 0041).

What the server refuses with ("Email or password is incorrect.", "Put the
pin on the water: …") is shown as it comes (frontend `err.message`), so it is
translated here, by hand, and the exception handler in main.py picks the
language from the visitor's choice (the `fisheye.lang` cookie the frontend
sets, sent with every API call). A message not listed stays in English: the
admin console's, and the ones only a script would see.

Keyed by the English. A message with something in it (a number, a fish) is a
pattern; fish named in the photo check's messages are named in the reader's
language, as the site's own pages name them (frontend i18n/names.ts).
"""
from __future__ import annotations

import re
from collections.abc import Callable

LANGS = ("zh", "es", "ko", "ja")
LANG_COOKIE = "fisheye.lang"  # frontend src/i18n/config.ts LOCALE_COOKIE

TEXT: dict[str, dict[str, str]] = {
    # --- signing in and the account
    "Email or password is incorrect.": {
        "zh": "邮箱或密码不正确。", "es": "El correo o la contraseña no son correctos.",
        "ko": "이메일 또는 비밀번호가 맞지 않아요.", "ja": "メールアドレスまたはパスワードが正しくありません。",
    },
    "Too many attempts. Wait a few minutes and try again.": {
        "zh": "尝试次数太多了，请过几分钟再试。", "es": "Demasiados intentos. Espera unos minutos y vuelve a intentarlo.",
        "ko": "시도 횟수가 너무 많아요. 몇 분 뒤에 다시 시도하세요.", "ja": "試行回数が多すぎます。数分待ってからもう一度お試しください。",
    },
    "An account with this email already exists. Sign in instead.": {
        "zh": "这个邮箱已经注册过了，请直接登录。", "es": "Ya existe una cuenta con este correo. Inicia sesión.",
        "ko": "이 이메일로 만든 계정이 이미 있어요. 로그인하세요.", "ja": "このメールアドレスのアカウントはすでにあります。ログインしてください。",
    },
    "That doesn't look like an email address.": {
        "zh": "这看起来不像邮箱地址。", "es": "Eso no parece un correo electrónico.",
        "ko": "이메일 주소가 아닌 것 같아요.", "ja": "メールアドレスの形式ではないようです。",
    },
    "Display names are 2 to 40 characters.": {
        "zh": "显示名称需要 2 到 40 个字符。", "es": "El nombre visible debe tener de 2 a 40 caracteres.",
        "ko": "표시 이름은 2~40자여야 해요.", "ja": "表示名は2〜40文字にしてください。",
    },
    "Display names can't contain control characters.": {
        "zh": "显示名称不能包含控制字符。", "es": "El nombre visible no puede tener caracteres de control.",
        "ko": "표시 이름에는 제어 문자를 쓸 수 없어요.", "ja": "表示名に制御文字は使えません。",
    },
    "The password can't be only spaces.": {
        "zh": "密码不能只有空格。", "es": "La contraseña no puede ser solo espacios.",
        "ko": "비밀번호를 공백만으로 만들 수는 없어요.", "ja": "パスワードを空白だけにすることはできません。",
    },
    "That password is too common. Pick something less guessable.": {
        "zh": "这个密码太常见了，换一个不容易被猜到的。", "es": "Esa contraseña es demasiado común. Elige una más difícil de adivinar.",
        "ko": "너무 흔한 비밀번호예요. 추측하기 어려운 것으로 바꿔 주세요.", "ja": "よく使われるパスワードです。推測されにくいものにしてください。",
    },
    "The password can't be your email address.": {
        "zh": "密码不能和邮箱地址一样。", "es": "La contraseña no puede ser tu correo.",
        "ko": "비밀번호를 이메일 주소와 같게 할 수 없어요.", "ja": "パスワードをメールアドレスと同じにはできません。",
    },
    "This account is suspended.": {
        "zh": "这个账户已被停用。", "es": "Esta cuenta está suspendida.",
        "ko": "이 계정은 정지됐어요.", "ja": "このアカウントは停止されています。",
    },
    "That password is incorrect.": {
        "zh": "密码不正确。", "es": "Esa contraseña no es correcta.",
        "ko": "비밀번호가 맞지 않아요.", "ja": "パスワードが正しくありません。",
    },
    "Your password is incorrect.": {
        "zh": "密码不正确。", "es": "Tu contraseña no es correcta.",
        "ko": "비밀번호가 맞지 않아요.", "ja": "パスワードが正しくありません。",
    },
    "Your current password is incorrect.": {
        "zh": "当前密码不正确。", "es": "Tu contraseña actual no es correcta.",
        "ko": "현재 비밀번호가 맞지 않아요.", "ja": "現在のパスワードが正しくありません。",
    },
    "Set a password first, or you'd have no way to sign in.": {
        "zh": "请先设置密码，否则你将无法登录。", "es": "Primero crea una contraseña; si no, no tendrías forma de iniciar sesión.",
        "ko": "먼저 비밀번호를 설정하세요. 그러지 않으면 로그인할 방법이 없어요.", "ja": "先にパスワードを設定してください。設定しないとログインできなくなります。",
    },
    "You're the only admin. Make someone else an admin first.": {
        "zh": "你是唯一的管理员，请先把别人设为管理员。", "es": "Eres el único administrador. Primero haz administrador a alguien más.",
        "ko": "관리자가 나뿐이에요. 먼저 다른 사람을 관리자로 지정하세요.", "ja": "管理者はあなただけです。先にほかの人を管理者にしてください。",
    },
    "Sign in to do that.": {
        "zh": "请先登录。", "es": "Inicia sesión para hacer eso.",
        "ko": "로그인한 뒤에 할 수 있어요.", "ja": "ログインしてから操作してください。",
    },
    "We couldn't send the email. Try again later.": {
        "zh": "邮件发送失败，请稍后再试。", "es": "No pudimos enviar el correo. Intenta más tarde.",
        "ko": "메일을 보내지 못했어요. 나중에 다시 시도하세요.", "ja": "メールを送れませんでした。しばらくしてからもう一度お試しください。",
    },
    "Confirm your email address first: open the link we emailed you, or send a new one from your account page.": {
        "zh": "请先确认你的邮箱：打开我们发给你的链接，或者在账户页重新发送一个。",
        "es": "Primero confirma tu correo: abre el enlace que te enviamos o pide uno nuevo desde tu cuenta.",
        "ko": "먼저 이메일 주소를 확인해 주세요. 보내 드린 링크를 열거나, 계정 페이지에서 새 링크를 보내세요.",
        "ja": "先にメールアドレスを確認してください。お送りしたリンクを開くか、アカウントページから新しいリンクを送ってください。",
    },
    "This link has already been used or isn't valid. Send a new one from your account page.": {
        "zh": "这个链接已经用过或者无效。请在账户页重新发送一个。",
        "es": "Este enlace ya se usó o no es válido. Pide uno nuevo desde tu cuenta.",
        "ko": "이미 사용했거나 유효하지 않은 링크예요. 계정 페이지에서 새 링크를 보내세요.",
        "ja": "このリンクは使用済みか無効です。アカウントページから新しいリンクを送ってください。",
    },
    "This link has expired. Send a new one from your account page.": {
        "zh": "这个链接已过期。请在账户页重新发送一个。", "es": "Este enlace venció. Pide uno nuevo desde tu cuenta.",
        "ko": "링크가 만료됐어요. 계정 페이지에서 새 링크를 보내세요.", "ja": "リンクの有効期限が切れました。アカウントページから新しいリンクを送ってください。",
    },
    "This link isn't valid any more.": {
        "zh": "这个链接已经失效了。", "es": "Este enlace ya no es válido.",
        "ko": "더 이상 유효하지 않은 링크예요.", "ja": "このリンクはもう使えません。",
    },
    "Google sign-in isn't configured.": {
        "zh": "这个服务器没有设置 Google 登录。", "es": "El inicio de sesión con Google no está configurado.",
        "ko": "Google 로그인이 설정되어 있지 않아요.", "ja": "Googleログインは設定されていません。",
    },
    "Google sign-in didn't complete. Try again.": {
        "zh": "Google 登录没有完成，请重试。", "es": "El inicio de sesión con Google no se completó. Intenta de nuevo.",
        "ko": "Google 로그인이 끝나지 않았어요. 다시 시도하세요.", "ja": "Googleでのログインが完了しませんでした。もう一度お試しください。",
    },
    "Google didn't return an email address.": {
        "zh": "Google 没有提供邮箱地址。", "es": "Google no devolvió un correo electrónico.",
        "ko": "Google에서 이메일 주소를 받지 못했어요.", "ja": "Googleからメールアドレスを受け取れませんでした。",
    },
    "Your Google email address isn't verified.": {
        "zh": "你的 Google 邮箱还没验证。", "es": "Tu correo de Google no está verificado.",
        "ko": "Google 이메일 주소가 인증되지 않았어요.", "ja": "Googleのメールアドレスが確認されていません。",
    },
    "That Google account is connected to a different FishEye account.": {
        "zh": "这个 Google 账户已经连接了另一个 FishEye 账户。", "es": "Esa cuenta de Google está conectada a otra cuenta de FishEye.",
        "ko": "이 Google 계정은 다른 FishEye 계정에 연결되어 있어요.", "ja": "そのGoogleアカウントは、別のFishEyeアカウントに連携されています。",
    },
    "Sign in with your password, then connect Google from your account page.": {
        "zh": "请先用密码登录，再在账户页连接 Google。", "es": "Inicia sesión con tu contraseña y luego conecta Google desde tu cuenta.",
        "ko": "비밀번호로 로그인한 다음, 계정 페이지에서 Google을 연결하세요.", "ja": "パスワードでログインしてから、アカウントページでGoogleを連携してください。",
    },
    # --- catches and photos
    "Put the pin on a lake or river in the United States: FishEye doesn't cover anywhere else yet.": {
        "zh": "请把图钉放在美国的湖泊或河流上：FishEye 暂时还不覆盖其他地方。",
        "es": "Pon el pin en un lago o río de Estados Unidos: FishEye todavía no cubre otros lugares.",
        "ko": "미국의 호수나 강에 핀을 놓아 주세요. FishEye는 아직 다른 곳을 지원하지 않아요.",
        "ja": "アメリカの湖か川にピンを置いてください。FishEyeはまだほかの場所に対応していません。",
    },
    "This reset link has expired or was already used. Ask for a new one.": {
        "zh": "这个重置链接已过期或已被使用，请重新申请。",
        "es": "Este enlace ya caducó o ya se usó. Pide uno nuevo.",
        "ko": "이 재설정 링크는 만료되었거나 이미 사용되었어요. 새 링크를 요청하세요.",
        "ja": "この再設定リンクは期限切れか、すでに使用されています。新しいリンクを依頼してください。",
    },
    "You've sent a lot today. Thanks! Try again tomorrow.": {
        "zh": "你今天已经发了很多条，谢谢！明天再试吧。",
        "es": "Hoy ya enviaste muchos. ¡Gracias! Inténtalo mañana.",
        "ko": "오늘 많이 보내 주셨어요. 감사합니다! 내일 다시 시도해 주세요.",
        "ja": "今日はたくさん送っていただきました。ありがとうございます！また明日お試しください。",
    },
    "Write a few words first.": {
        "zh": "请先写几个字。", "es": "Escribe unas palabras primero.",
        "ko": "먼저 몇 마디 적어 주세요.", "ja": "先に何か書いてください。",
    },
    "AI summaries are paused until next month. The fish guides, the map and Ask's answers from the guides still work.": {
        "zh": "AI 总结暂停到下个月。鱼类指南、地图和 Ask 里来自指南的回答都还能用。",
        "es": "Los resúmenes con IA están en pausa hasta el próximo mes. Las guías de peces, el mapa y las respuestas de Ask basadas en las guías siguen funcionando.",
        "ko": "AI 요약은 다음 달까지 일시 중지돼요. 어종 가이드, 지도, 가이드 기반 Ask 답변은 계속 쓸 수 있어요.",
        "ja": "AI要約は来月まで停止しています。魚のガイド、地図、ガイドに基づくAskの回答は引き続き使えます。",
    },
    "That name is reserved. Pick another.": {
        "zh": "这个名字已被保留，请换一个。", "es": "Ese nombre está reservado. Elige otro.",
        "ko": "예약된 이름이에요. 다른 이름을 골라 주세요.", "ja": "その名前は予約されています。別の名前を選んでください。",
    },
    "That has characters FishEye can't read. Check what you typed and try again.": {
        "zh": "内容里有 FishEye 读不了的字符，请检查后再试。",
        "es": "Hay caracteres que FishEye no puede leer. Revisa lo que escribiste e inténtalo de nuevo.",
        "ko": "FishEye가 읽을 수 없는 문자가 있어요. 입력한 내용을 확인하고 다시 시도하세요.",
        "ja": "FishEyeが読めない文字が含まれています。入力内容を確認して、もう一度お試しください。",
    },
    "Put the pin on the water: a lake, pond or river that has a name on the map, or its bank.": {
        "zh": "请把标记放到水上：地图上有名字的湖、池塘或河流，或者它的岸边。",
        "es": "Pon el marcador en el agua: un lago, estanque o río con nombre en el mapa, o su orilla.",
        "ko": "핀을 물 위에 놓아 주세요. 지도에 이름이 나오는 호수, 연못, 강이나 그 물가여야 해요.",
        "ja": "ピンを水の上に置いてください：地図上で名前のある湖・池・川、またはその岸です。",
    },
    "Add a photo of the fish: a catch that names a species needs one, and FishEye checks it.": {
        "zh": "请加一张鱼的照片：写明鱼种的渔获需要照片，FishEye 会核对。",
        "es": "Agrega una foto del pez: una captura que nombra una especie la necesita, y FishEye la revisa.",
        "ko": "물고기 사진을 추가하세요. 어종을 적은 조과에는 사진이 필요하고, FishEye가 확인해요.",
        "ja": "魚の写真を追加してください。魚種を書いた釣果には写真が必要で、FishEyeが確認します。",
    },
    "Give the catch a title of 3 to 80 characters.": {
        "zh": "标题需要 3 到 80 个字符。", "es": "El título debe tener de 3 a 80 caracteres.",
        "ko": "제목은 3~80자로 적어 주세요.", "ja": "タイトルは3〜80文字にしてください。",
    },
    "Pick a species from the list, or use 'Other'.": {
        "zh": "请从列表里选一种鱼，或者选“其他”。", "es": "Elige una especie de la lista, o usa «Otro».",
        "ko": "목록에서 어종을 고르거나 ‘기타’를 선택하세요.", "ja": "リストから魚種を選ぶか、「その他」を選んでください。",
    },
    "Visibility is public or private.": {
        "zh": "公开范围只能是公开或仅自己。", "es": "La visibilidad es pública o privada.",
        "ko": "공개 범위는 공개 또는 비공개만 돼요.", "ja": "公開範囲は「公開」か「自分のみ」です。",
    },
    "That date doesn't look right.": {
        "zh": "这个日期看起来不对。", "es": "Esa fecha no parece correcta.",
        "ko": "날짜가 올바르지 않은 것 같아요.", "ja": "日付が正しくないようです。",
    },
    "That location isn't valid.": {
        "zh": "这个位置无效。", "es": "Esa ubicación no es válida.",
        "ko": "올바른 위치가 아니에요.", "ja": "その位置は無効です。",
    },
    "Send both latitude and longitude, or neither.": {
        "zh": "请同时提供纬度和经度，或者都不提供。", "es": "Envía la latitud y la longitud juntas, o ninguna.",
        "ko": "위도와 경도를 함께 보내거나, 둘 다 보내지 마세요.", "ja": "緯度と経度は両方送るか、どちらも送らないでください。",
    },
    "Only the person who shared this catch can change it.": {
        "zh": "只有分享这条渔获的人才能修改它。", "es": "Solo quien compartió esta captura puede cambiarla.",
        "ko": "이 조과를 공유한 사람만 바꿀 수 있어요.", "ja": "この釣果を投稿した人だけが変更できます。",
    },
    "Choose at least one photo.": {
        "zh": "请至少选一张照片。", "es": "Elige al menos una foto.",
        "ko": "사진을 한 장 이상 고르세요.", "ja": "写真を1枚以上選んでください。",
    },
    "No such photo.": {
        "zh": "找不到这张照片。", "es": "No existe esa foto.",
        "ko": "그런 사진이 없어요.", "ja": "その写真は見つかりません。",
    },
    "That file is empty.": {
        "zh": "这个文件是空的。", "es": "Ese archivo está vacío.",
        "ko": "빈 파일이에요.", "ja": "ファイルが空です。",
    },
    "Upload a JPEG, PNG or WebP photo.": {
        "zh": "请上传 JPEG、PNG 或 WebP 照片。", "es": "Sube una foto JPEG, PNG o WebP.",
        "ko": "JPEG, PNG, WebP 사진을 올려 주세요.", "ja": "JPEG・PNG・WebPの写真をアップロードしてください。",
    },
    "That image is too large.": {
        "zh": "这张图片太大了。", "es": "Esa imagen es demasiado grande.",
        "ko": "이미지가 너무 커요.", "ja": "画像が大きすぎます。",
    },
    "That upload is too large.": {
        "zh": "上传的文件太大了。", "es": "Lo que subiste es demasiado grande.",
        "ko": "업로드한 파일이 너무 커요.", "ja": "アップロードしたファイルが大きすぎます。",
    },
    "That file isn't a photo we can read.": {
        "zh": "这个文件不是我们能读取的照片。", "es": "Ese archivo no es una foto que podamos leer.",
        "ko": "읽을 수 있는 사진 파일이 아니에요.", "ja": "読み込める写真ではありません。",
    },
    "The photo check isn't available right now. Try again later.": {
        "zh": "照片核对暂时不可用，请稍后再试。", "es": "La revisión de fotos no está disponible ahora. Intenta más tarde.",
        "ko": "지금은 사진 확인을 쓸 수 없어요. 나중에 다시 시도하세요.", "ja": "写真チェックは現在使えません。しばらくしてからもう一度お試しください。",
    },
    "You're doing that a lot. Try again later.": {
        "zh": "操作太频繁了，请稍后再试。", "es": "Lo estás haciendo muchas veces. Intenta más tarde.",
        "ko": "너무 자주 시도했어요. 나중에 다시 시도하세요.", "ja": "操作が多すぎます。しばらくしてからもう一度お試しください。",
    },
    "Pick a reason.": {
        "zh": "请选一个原因。", "es": "Elige un motivo.",
        "ko": "사유를 고르세요.", "ja": "理由を選んでください。",
    },
    "You can't report your own catch.": {
        "zh": "不能举报自己的渔获。", "es": "No puedes reportar tu propia captura.",
        "ko": "내 조과는 신고할 수 없어요.", "ja": "自分の釣果は通報できません。",
    },
    "You've already reported this catch.": {
        "zh": "你已经举报过这条渔获。", "es": "Ya reportaste esta captura.",
        "ko": "이미 신고한 조과예요.", "ja": "この釣果はすでに通報済みです。",
    },
    "You've already reported this catch. A moderator will look at it.": {
        "zh": "你已经举报过这条渔获，管理员会处理。", "es": "Ya reportaste esta captura. Un moderador la revisará.",
        "ko": "이미 신고한 조과예요. 운영자가 확인할 거예요.", "ja": "この釣果はすでに通報済みです。運営が確認します。",
    },
    "We couldn't find a fish in this photo. Use one that shows the whole fish, side-on.": {
        "zh": "照片里没找到鱼。换一张能看到整条鱼侧面的照片。",
        "es": "No encontramos un pez en esta foto. Usa una que muestre el pez completo, de lado.",
        "ko": "이 사진에서 물고기를 찾지 못했어요. 물고기 전체가 옆에서 보이는 사진을 써 주세요.",
        "ja": "この写真に魚が見つかりませんでした。魚全体を横から写した写真を使ってください。",
    },
    "There's a fish in this photo.": {
        "zh": "照片里有鱼。", "es": "Hay un pez en esta foto.",
        "ko": "이 사진에 물고기가 있어요.", "ja": "この写真には魚が写っています。",
    },
    "No such catch.": {
        "zh": "找不到这条渔获。", "es": "No existe esa captura.",
        "ko": "그런 조과가 없어요.", "ja": "その釣果は見つかりません。",
    },
    "This catch is under moderation, so it can't be changed until a moderator reviews it. You can still delete it.": {
        "zh": "这条渔获正在审核中，审核完成前不能修改，但可以删除。",
        "es": "Esta captura está en revisión, así que no se puede cambiar hasta que un moderador la revise. Todavía puedes borrarla.",
        "ko": "이 조과는 검토 중이라 운영자가 검토할 때까지 수정할 수 없어요. 삭제는 할 수 있어요.",
        "ja": "この釣果は確認中のため、運営の確認が終わるまで変更できません。削除はできます。",
    },
    "This is the photo that shows your fish, so it stays while the catch names a species. Change the fish to “Not sure” first, or delete the catch.": {
        "zh": "这是能看出鱼种的那张照片，渔获写着鱼种时必须保留。请先把鱼种改成“不确定”，或者删除这条渔获。",
        "es": "Esta es la foto que muestra tu pez, así que se queda mientras la captura nombre una especie. Primero cambia el pez a «No sé», o borra la captura.",
        "ko": "어종을 보여 주는 사진이라, 조과에 어종이 적혀 있는 동안은 지울 수 없어요. 먼저 어종을 ‘모름’으로 바꾸거나 조과를 삭제하세요.",
        "ja": "魚種を確かめた写真なので、釣果に魚種がある間は削除できません。先に魚を「わからない」に変えるか、釣果を削除してください。",
    },
    "For your security, confirm it's you first.": {
        "zh": "为了安全，请先确认是你本人。", "es": "Por tu seguridad, primero confirma que eres tú.",
        "ko": "보안을 위해 먼저 본인 확인을 해 주세요.", "ja": "安全のため、先に本人確認をしてください。",
    },
    # --- slurs (services/word_filter.py)
    "That name includes a word FishEye doesn't allow.": {
        "zh": "这个名字里有 FishEye 不允许使用的词。", "es": "Ese nombre incluye una palabra que FishEye no permite.",
        "ko": "이 이름에는 FishEye에서 쓸 수 없는 말이 들어 있어요.", "ja": "この名前には、FishEyeで使えない言葉が含まれています。",
    },
    "The title includes a word FishEye doesn't allow.": {
        "zh": "标题里有 FishEye 不允许使用的词。", "es": "El título incluye una palabra que FishEye no permite.",
        "ko": "제목에 FishEye에서 쓸 수 없는 말이 들어 있어요.", "ja": "タイトルに、FishEyeで使えない言葉が含まれています。",
    },
    "The notes include a word FishEye doesn't allow.": {
        "zh": "备注里有 FishEye 不允许使用的词。", "es": "Las notas incluyen una palabra que FishEye no permite.",
        "ko": "메모에 FishEye에서 쓸 수 없는 말이 들어 있어요.", "ja": "メモに、FishEyeで使えない言葉が含まれています。",
    },
    "The fish's name includes a word FishEye doesn't allow.": {
        "zh": "鱼名里有 FishEye 不允许使用的词。", "es": "El nombre del pez incluye una palabra que FishEye no permite.",
        "ko": "물고기 이름에 FishEye에서 쓸 수 없는 말이 들어 있어요.", "ja": "魚の名前に、FishEyeで使えない言葉が含まれています。",
    },
    # --- lake reports
    "You've sent a lot of reports. Try again later.": {
        "zh": "你提交的报告太多了，请稍后再试。", "es": "Has enviado muchos reportes. Intenta más tarde.",
        "ko": "제보를 너무 많이 보냈어요. 나중에 다시 시도하세요.", "ja": "報告の送信が多すぎます。しばらくしてからもう一度お試しください。",
    },
    "Give the lake's name.": {
        "zh": "请写上湖名。", "es": "Escribe el nombre del lago.",
        "ko": "호수 이름을 적어 주세요.", "ja": "湖の名前を入力してください。",
    },
    "Put the map on the lake first.": {
        "zh": "请先把地图移到这个湖上。", "es": "Primero pon el mapa sobre el lago.",
        "ko": "먼저 지도를 호수 위로 옮겨 주세요.", "ja": "先に地図を湖の上に動かしてください。",
    },
    "Pick what's wrong.": {
        "zh": "请选择哪里不对。", "es": "Elige qué está mal.",
        "ko": "잘못된 점을 고르세요.", "ja": "誤りの内容を選んでください。",
    },
    "Say what's wrong.": {
        "zh": "请写一下哪里不对。", "es": "Di qué está mal.",
        "ko": "무엇이 잘못됐는지 적어 주세요.", "ja": "どこが違うか書いてください。",
    },
    "No such lake.": {
        "zh": "找不到这个湖。", "es": "No existe ese lago.",
        "ko": "그런 호수가 없어요.", "ja": "その湖は見つかりません。",
    },
    # --- location search, and requests over a limit
    "Location search is temporarily unavailable. Please try again shortly.": {
        "zh": "地点搜索暂时不可用，请稍后再试。", "es": "La búsqueda de lugares no está disponible por ahora. Intenta en un rato.",
        "ko": "위치 검색을 잠시 쓸 수 없어요. 잠시 후 다시 시도하세요.", "ja": "場所の検索が一時的に使えません。少ししてからもう一度お試しください。",
    },
    "That's a lot of requests in a short time. Please wait a moment and try again.": {
        "zh": "短时间内请求太多了，请稍等一下再试。", "es": "Son muchas solicitudes en poco tiempo. Espera un momento y vuelve a intentarlo.",
        "ko": "짧은 시간에 요청이 너무 많아요. 잠시 기다렸다가 다시 시도하세요.", "ja": "短時間にリクエストが多すぎます。少し待ってからもう一度お試しください。",
    },
    "This feature is at its limit for now. Please try again later.": {
        "zh": "这个功能暂时达到上限了，请稍后再试。", "es": "Esta función llegó a su límite por ahora. Intenta más tarde.",
        "ko": "이 기능은 지금 한도에 도달했어요. 나중에 다시 시도하세요.", "ja": "この機能は現在上限に達しています。しばらくしてからもう一度お試しください。",
    },
    "The AI features have reached today's limit for everyone. The fish guides and the map still work; please try again tomorrow.": {
        "zh": "今天所有人的 AI 功能都用到上限了。鱼类指南和地图照常可用，请明天再试。",
        "es": "Las funciones de IA llegaron al límite de hoy para todos. Las guías y el mapa siguen funcionando; intenta mañana.",
        "ko": "오늘은 모든 사용자의 AI 기능이 한도에 도달했어요. 어종 가이드와 지도는 계속 쓸 수 있으니, 내일 다시 시도하세요.",
        "ja": "本日のAI機能は全体の上限に達しました。魚ガイドと地図は引き続き使えます。明日またお試しください。",
    },
    "AI summaries are for fishing questions the FishEye guides cover, and the guides don't cover this one. Nothing was used from today's allowance.": {
        "zh": "AI 摘要只用于 FishEye 指南覆盖的钓鱼问题，这个问题不在其中。今天的次数没有被扣。",
        "es": "Los resúmenes con IA son para preguntas de pesca que cubren las guías de FishEye, y esta no. No se usó nada de lo de hoy.",
        "ko": "AI 요약은 FishEye 가이드에 나오는 낚시 질문에만 쓸 수 있는데, 이 질문은 해당하지 않아요. 오늘 사용량은 차감되지 않았어요.",
        "ja": "AI要約はFishEyeのガイドにある釣りの質問だけが対象で、この質問は含まれません。今日の回数は使われていません。",
    },
}

# Guide fish and the photo check's look-alike groups, by the English the
# server says them in (frontend i18n/names.ts FISH_NAMES, GROUP_NAMES).
FISH: dict[str, dict[str, str]] = {
    "Largemouth Bass": {"zh": "大口黑鲈", "es": "lobina negra", "ko": "큰입배스", "ja": "ラージマウスバス"},
    "Smallmouth Bass": {"zh": "小口黑鲈", "es": "lobina de boca chica", "ko": "작은입배스", "ja": "スモールマウスバス"},
    "Spotted Bass": {"zh": "斑点黑鲈", "es": "lobina manchada", "ko": "스포티드배스", "ja": "スポッテッドバス"},
    "Guadalupe Bass": {"zh": "瓜达卢佩鲈", "es": "lobina de Guadalupe", "ko": "과달루페배스", "ja": "グアダルーペバス"},
    "White Bass": {"zh": "白鲈", "es": "lobina blanca", "ko": "화이트배스", "ja": "ホワイトバス"},
    "Striped Bass": {"zh": "条纹鲈", "es": "lobina rayada", "ko": "스트라이프드배스", "ja": "ストライプドバス"},
    "Hybrid Striped Bass": {"zh": "杂交条纹鲈", "es": "lobina rayada híbrida", "ko": "하이브리드 스트라이프드배스", "ja": "ハイブリッドストライプドバス"},
    "Channel Catfish": {"zh": "斑点叉尾鮰", "es": "bagre de canal", "ko": "채널메기", "ja": "チャネルキャットフィッシュ"},
    "Blue Catfish": {"zh": "蓝鲶", "es": "bagre azul", "ko": "블루메기", "ja": "ブルーキャットフィッシュ"},
    "Flathead Catfish": {"zh": "扁头鲶", "es": "bagre cabeza plana", "ko": "플랫헤드메기", "ja": "フラットヘッドキャットフィッシュ"},
    "White Crappie": {"zh": "白莓鲈", "es": "crappie blanco", "ko": "화이트크래피", "ja": "ホワイトクラッピー"},
    "Black Crappie": {"zh": "黑莓鲈", "es": "crappie negro", "ko": "블랙크래피", "ja": "ブラッククラッピー"},
    "Bluegill": {"zh": "蓝鳃太阳鱼", "es": "mojarra de agallas azules", "ko": "블루길", "ja": "ブルーギル"},
    "Redear Sunfish": {"zh": "红耳太阳鱼", "es": "mojarra de oreja roja", "ko": "레드이어선피시", "ja": "レッドイヤーサンフィッシュ"},
    "Rainbow Trout": {"zh": "虹鳟", "es": "trucha arcoíris", "ko": "무지개송어", "ja": "ニジマス"},
    "Freshwater Drum": {"zh": "淡水鼓鱼", "es": "corvina de agua dulce", "ko": "민물드럼", "ja": "フレッシュウォータードラム"},
    "Common Carp": {"zh": "鲤鱼", "es": "carpa común", "ko": "잉어", "ja": "コイ"},
    "Walleye": {"zh": "大眼鲈", "es": "walleye", "ko": "월아이", "ja": "ウォールアイ"},
    "Northern Pike": {"zh": "白斑狗鱼", "es": "lucio norteño", "ko": "노던파이크", "ja": "ノーザンパイク"},
    "Yellow Perch": {"zh": "黄金鲈", "es": "perca amarilla", "ko": "옐로퍼치", "ja": "イエローパーチ"},
    "Brook Trout": {"zh": "溪红点鲑", "es": "trucha de arroyo", "ko": "브룩송어", "ja": "ブルックトラウト"},
    "Brown Trout": {"zh": "褐鳟", "es": "trucha marrón", "ko": "브라운송어", "ja": "ブラウントラウト"},
    "Golden Trout": {"zh": "金鳟", "es": "trucha dorada", "ko": "골든송어", "ja": "ゴールデントラウト"},
    "Cutthroat Trout": {"zh": "切喉鳟", "es": "trucha degollada", "ko": "컷스로트송어", "ja": "カットスロートトラウト"},
    "Kokanee Salmon": {"zh": "科卡尼鲑", "es": "salmón kokanee", "ko": "코카니연어", "ja": "ヒメマス"},
    "Brown Bullhead": {"zh": "云斑鮰", "es": "bagre torito", "ko": "브라운불헤드", "ja": "ブラウンブルヘッド"},
    "Gizzard Shad": {"zh": "美洲真鰶", "es": "sardina molleja", "ko": "기자드섀드", "ja": "ギザードシャッド"},
    "Threadfin Shad": {"zh": "线鳍鲥", "es": "sardina maya", "ko": "스레드핀섀드", "ja": "スレッドフィンシャッド"},
    # groups, without their "a"
    "black bass": {"zh": "黑鲈", "es": "lobina", "ko": "배스류", "ja": "ブラックバスの仲間"},
    "carp": {"zh": "鲤鱼", "es": "carpa", "ko": "잉어류", "ja": "コイの仲間"},
    "catfish": {"zh": "鲶鱼", "es": "bagre", "ko": "메기류", "ja": "ナマズの仲間"},
    "crappie": {"zh": "莓鲈", "es": "crappie", "ko": "크래피류", "ja": "クラッピーの仲間"},
    "shad": {"zh": "鲥鱼", "es": "sardina", "ko": "섀드류", "ja": "シャッドの仲間"},
    "sunfish": {"zh": "太阳鱼", "es": "mojarra", "ko": "선피시류", "ja": "サンフィッシュの仲間"},
    "trout": {"zh": "鳟鱼", "es": "trucha", "ko": "송어류", "ja": "マスの仲間"},
    "white or striped bass": {"zh": "白鲈或条纹鲈", "es": "lobina blanca o rayada", "ko": "화이트배스 또는 스트라이프드배스", "ja": "ホワイトバスかストライプドバス"},
}


def _fish(english: str, lang: str) -> str:
    """"a Channel Catfish" → its name in `lang`; a fish the site has no name
    for stays as the server named it, without the "a"."""
    bare = re.sub(r"^an? ", "", english.strip())
    return FISH.get(bare, {}).get(lang) or FISH.get(bare.lower(), {}).get(lang) or bare


_A = r"(an? [^.,]+?)"
Pattern = tuple[re.Pattern[str], Callable[[re.Match[str], str], str | None]]
PATTERNS: list[Pattern] = [
    (re.compile(r"^Use at least (\d+) characters\.$"),
     lambda m, lang: {"zh": f"密码至少要 {m[1]} 个字符。", "es": f"Usa al menos {m[1]} caracteres.",
                   "ko": f"비밀번호는 {m[1]}자 이상이어야 해요.", "ja": f"パスワードは{m[1]}文字以上にしてください。"}[lang]),
    (re.compile(r"^Use at most (\d+) characters\.$"),
     lambda m, lang: {"zh": f"密码最多 {m[1]} 个字符。", "es": f"Usa como máximo {m[1]} caracteres.",
                   "ko": f"비밀번호는 {m[1]}자 이하여야 해요.", "ja": f"パスワードは{m[1]}文字以内にしてください。"}[lang]),
    (re.compile(r"^A catch can have up to (\d+) photos\.$"),
     lambda m, lang: {"zh": f"每条渔获最多 {m[1]} 张照片。", "es": f"Una captura puede tener hasta {m[1]} fotos.",
                   "ko": f"조과 하나에 사진은 {m[1]}장까지예요.", "ja": f"写真は1件の釣果につき{m[1]}枚までです。"}[lang]),
    (re.compile(r"^Photos can be up to (\d+) MB\.$"),
     lambda m, lang: {"zh": f"每张照片最大 {m[1]} MB。", "es": f"Las fotos pueden pesar hasta {m[1]} MB.",
                   "ko": f"사진은 {m[1]}MB까지 올릴 수 있어요.", "ja": f"写真は{m[1]} MBまでです。"}[lang]),
    (re.compile(r"^Keep it under (\d+) characters\.$"),
     lambda m, lang: {"zh": f"请控制在 {m[1]} 个字符以内。", "es": f"Que no pase de {m[1]} caracteres.",
                   "ko": f"{m[1]}자 이내로 적어 주세요.", "ja": f"{m[1]}文字以内にしてください。"}[lang]),
    (re.compile(r"^No location found for (['\"]?)(.*)\1\.$"),
     lambda m, lang: {"zh": f"找不到“{m[2]}”。", "es": f"No encontramos «{m[2]}».",
                   "ko": f"‘{m[2]}’ 검색 결과가 없어요.", "ja": f"「{m[2]}」が見つかりませんでした。"}[lang]),
    (re.compile(r"^New accounts can share (\d+) catches a day for their first (\d+) days\. Try again tomorrow\.$"),
     lambda m, lang: {"zh": f"新账户在前 {m[2]} 天每天最多分享 {m[1]} 条渔获，请明天再试。",
                   "es": f"Las cuentas nuevas pueden compartir {m[1]} capturas al día durante sus primeros {m[2]} días. Intenta mañana.",
                   "ko": f"새 계정은 처음 {m[2]}일 동안 하루에 조과를 {m[1]}건까지 공유할 수 있어요. 내일 다시 시도하세요.",
                   "ja": f"新しいアカウントは、最初の{m[2]}日間は1日{m[1]}件まで釣果を投稿できます。明日またお試しください。"}[lang]),
    (re.compile(r"^You've used today's (\d+) AI summaries\. Searching the guides is still free; summaries come back tomorrow \(UTC\)\.$"),
     lambda m, lang: {"zh": f"今天的 {m[1]} 次 AI 摘要已经用完了。搜索指南仍然免费；摘要明天（UTC）恢复。",
                   "es": f"Ya usaste los {m[1]} resúmenes con IA de hoy. Buscar en las guías sigue siendo gratis; los resúmenes vuelven mañana (UTC).",
                   "ko": f"오늘 쓸 수 있는 AI 요약 {m[1]}회를 다 썼어요. 가이드 검색은 계속 무료이고, 요약은 내일(UTC) 다시 쓸 수 있어요.",
                   "ja": f"今日のAI要約（{m[1]}回）はすべて使いました。ガイドの検索は引き続き無料で、要約は明日（UTC）また使えます。"}[lang]),
    (re.compile(r"^Photo (\d+): (.+)$"),
     lambda m, lang: {"zh": f"第 {m[1]} 张照片：{tr(m[2], lang)}", "es": f"Foto {m[1]}: {tr(m[2], lang)}",
                   "ko": f"사진 {m[1]}: {tr(m[2], lang)}", "ja": f"写真{m[1]}：{tr(m[2], lang)}"}[lang]),
    # The photo check (services/fish_id.py check_claim).
    (re.compile(rf"^This looks like {_A}\. Pick it from the list instead of Other\.$"),
     lambda m, lang: {"zh": f"这看起来是{_fish(m[1], lang)}。请在列表里选它，不要选“其他”。",
                   "es": f"Parece ser {_fish(m[1], lang)}. Elígelo de la lista en lugar de Otro.",
                   "ko": f"{_fish(m[1], lang)}인 것 같아요. ‘기타’ 대신 목록에서 고르세요.",
                   "ja": f"{_fish(m[1], lang)}のようです。「その他」ではなくリストから選んでください。"}[lang]),
    (re.compile(rf"^Photo check: this looks like {_A}\.$"),
     lambda m, lang: {"zh": f"照片核对：看起来是{_fish(m[1], lang)}。", "es": f"Revisión de la foto: parece ser {_fish(m[1], lang)}.",
                   "ko": f"사진 확인: {_fish(m[1], lang)}인 것 같아요.", "ja": f"写真チェック：{_fish(m[1], lang)}のようです。"}[lang]),
    (re.compile(rf"^Photo check: this looks like {_A}\. Which kind, the photo can't show, so the species is your call\.$"),
     lambda m, lang: {"zh": f"照片核对：看起来是{_fish(m[1], lang)}。具体哪一种照片看不出来，由你判断。",
                   "es": f"Revisión de la foto: parece ser {_fish(m[1], lang)}. La especie exacta no se ve en la foto: la decides tú.",
                   "ko": f"사진 확인: {_fish(m[1], lang)}인 것 같아요. 정확한 종류는 사진으로 알 수 없으니 직접 판단하세요.",
                   "ja": f"写真チェック：{_fish(m[1], lang)}のようです。どの種類かは写真では分からないので、ご自身で判断してください。"}[lang]),
    (re.compile(rf"^This looks like {_A}, not {_A}\. It isn't on FishEye's list yet: choose Other and name it\.$"),
     lambda m, lang: {"zh": f"这看起来是{_fish(m[1], lang)}，不是{_fish(m[2], lang)}。它还不在 FishEye 的列表里：请选“其他”并写上名字。",
                   "es": f"Parece ser {_fish(m[1], lang)}, no {_fish(m[2], lang)}. Todavía no está en la lista de FishEye: elige Otro y escribe su nombre.",
                   "ko": f"{_fish(m[1], lang)}인 것 같아요({_fish(m[2], lang)} 아님). 아직 FishEye 목록에 없는 어종이니 ‘기타’를 고르고 이름을 적어 주세요.",
                   "ja": f"{_fish(m[2], lang)}ではなく{_fish(m[1], lang)}のようです。この魚はまだFishEyeのリストにないので、「その他」を選んで名前を入力してください。"}[lang]),
    (re.compile(rf"^This looks like {_A}, not {_A}\. Change the fish to ([^,]+), or use a photo of the (.+)\.$"),
     lambda m, lang: {"zh": f"这看起来是{_fish(m[1], lang)}，不是{_fish(m[2], lang)}。把鱼种改成{_fish(m[3], lang)}，或者换一张{_fish(m[4], lang)}的照片。",
                   "es": f"Parece ser {_fish(m[1], lang)}, no {_fish(m[2], lang)}. Cambia el pez a {_fish(m[3], lang)} o usa una foto de {_fish(m[4], lang)}.",
                   "ko": f"{_fish(m[1], lang)}인 것 같아요({_fish(m[2], lang)} 아님). 어종을 바꾸거나, {_fish(m[4], lang)} 사진을 올려 주세요.",
                   "ja": f"{_fish(m[2], lang)}ではなく{_fish(m[1], lang)}のようです。魚を{_fish(m[3], lang)}に変えるか、{_fish(m[4], lang)}の写真を使ってください。"}[lang]),
    (re.compile(rf"^We couldn't confirm this is {_A} from this photo\. Try one that shows the whole fish, side-on, in good light\.$"),
     lambda m, lang: {"zh": f"从这张照片确认不了是{_fish(m[1], lang)}。换一张光线好、能看到整条鱼侧面的照片。",
                   "es": f"Con esta foto no pudimos confirmar que sea {_fish(m[1], lang)}. Prueba una con buena luz que muestre el pez completo, de lado.",
                   "ko": f"이 사진으로는 {_fish(m[1], lang)}인지 확인하지 못했어요. 밝은 곳에서 물고기 전체를 옆에서 찍은 사진으로 다시 해 보세요.",
                   "ja": f"この写真では{_fish(m[1], lang)}だと確認できませんでした。明るい場所で魚全体を横から写した写真で試してください。"}[lang]),
]


def tr(message: str, lang: str | None) -> str:
    """`message` in `lang`, or as it was: English, a language this doesn't
    know, or a message without a translation."""
    if not lang or lang not in LANGS or not isinstance(message, str):
        return message
    found = TEXT.get(message)
    if found:
        return found[lang]
    for pattern, render in PATTERNS:
        m = pattern.match(message)
        if m:
            return render(m, lang) or message
    return message
