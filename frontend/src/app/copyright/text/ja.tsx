import Link from "next/link";

import { LEGAL, type LegalText } from "@/lib/legal";

import { NOTICE_SUBJECT, noticeHref } from "./en";

// Japanese translation of en.tsx, section for section. The English version
// is the one that applies. Change this with en.tsx.
// Each paragraph stays on one line: JSX turns a line break into a space.

function Body() {
  return (
    <>
      <section>
        <h2>ルールに違反する釣果</h2>
        <p>
          釣果を開き、<strong>通報</strong>を使ってください。理由（スパム、不適切な写真、間違った場所、私有地、危険または違法なもの）を選び、メモを添えてください。複数の人から通報された釣果は、モデレーターが確認するまで非表示になります。通報にはアカウントが必要なため、1人だけで釣果を非表示にすることはできません。
        </p>
        <p>
          ご自身の個人情報が他の人に投稿された場合や、釣果がご自身の土地に人を誘導している場合など、その他のことは、リンクを添えて<a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>までご連絡ください。
        </p>
      </section>

      <section>
        <h2>著作権に関する通知</h2>
        <p>
          FishEye上のものがご自身の著作物を許可なく使用している場合は、件名を「{NOTICE_SUBJECT}」（著作権に関する通知）として、次の事項を記載した通知を<a href={noticeHref}>{LEGAL.contactEmail}</a>までお送りください。
        </p>
        <ol>
          <li>侵害されていると主張する著作物</li>
          <li>それを使用しているFishEye上の釣果またはページへのリンク</li>
          <li>氏名、住所、電話番号、メールアドレス</li>
          <li>その使用が、ご自身、代理人、または法律によって許可されていないと誠実に信じている旨の陳述</li>
          <li>通知の情報が正確であること、および偽証罪の制裁の下で、ご自身が著作権者であるか著作権者のために行動する権限があることの陳述</li>
          <li>自筆または電子的な署名（氏名をフルネームで入力すれば足ります）</li>
        </ol>
        <p>
          当社はそのコンテンツを削除し、投稿者に知らせ、通知の写しを渡します。故意に虚偽の申し立てをした場合、申し立てた人が損害賠償責任を負うことがあります。
        </p>
      </section>

      <section>
        <h2>釣果が削除された場合</h2>
        <p>
          誤って削除された、または投稿する権利があると考える場合は、同じアドレスに異議申立通知を送ってください。記載事項は、削除されたものへのリンク、誤りまたは誤認によって削除されたと誠実に信じている旨の偽証罪の制裁の下での陳述、氏名、住所、電話番号、住所地を管轄する連邦裁判所（米国外の場合は、FishEyeが所在しうるいずれかの裁判所）の管轄に同意し、通知を送った人からの送達を受け入れる旨、および署名です。申し立てた人が10営業日以内に訴訟を起こしたことを当社に知らせない限り、当社はコンテンツを元に戻すことがあります。
        </p>
      </section>

      <section>
        <h2>繰り返し侵害する人</h2>
        <p>
          他人の著作権を侵害するコンテンツを繰り返し投稿する人のアカウントは閉鎖します。<Link href="/terms">利用規約</Link>もご覧ください。
        </p>
      </section>
    </>
  );
}

export const ja: LegalText = {
  title: "著作権とコンテンツ",
  lede: "ルールに違反する釣果や、権利者の許可なく投稿された写真や文章について、当社に知らせる方法です。",
  description: "ルールに違反する釣果や、著作権を侵害するコンテンツを報告する方法です。",
  Body,
};
