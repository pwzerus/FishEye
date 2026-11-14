// 由 zh.tsx 自動產生（frontend/scripts/zh_hant.py，OpenCC s2twp）。
// Generated from zh.tsx by scripts/zh_hant.py: edit zh.tsx and run it again, not this file.
import Link from "next/link";

import { LEGAL, type LegalText } from "@/lib/legal";

import { NOTICE_SUBJECT, noticeHref } from "./en";

// 版權頁的簡體中文譯文，逐節對應 en.tsx；以英文版為準。
// 改 en.tsx 時同步改這裡，然後在 frontend/ 下執行 scripts/zh_hant.py 生成繁體版。
// 每段寫在一行裡：JSX 會把換行變成空格。

function Body() {
  return (
    <>
      <section>
        <h2>違反規則的漁獲</h2>
        <p>
          開啟該漁獲，點選<strong>舉報</strong>。選擇原因（垃圾資訊、不當照片、位置錯誤、私人財產、不安全或違法的內容），並新增說明。被多人舉報的漁獲會被隱藏，直到管理員檢視。舉報需要帳戶，因此任何人都無法獨自隱藏一條漁獲。
        </p>
        <p>
          其他情況，例如他人發布了你的個人資訊，或某條漁獲引導他人進入你的土地：請將連結傳送至 <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>。
        </p>
      </section>

      <section>
        <h2>版權通知</h2>
        <p>
          如果 FishEye 上的內容未經許可使用了你享有版權的作品，請傳送通知至 <a href={noticeHref}>{LEGAL.contactEmail}</a>，郵件主題為「{NOTICE_SUBJECT}」（版權通知），並提供：
        </p>
        <ol>
          <li>你認為被侵權的作品；</li>
          <li>FishEye 上使用該作品的漁獲或頁面的連結；</li>
          <li>你的姓名、郵寄地址、電話號碼和電子郵件地址；</li>
          <li>一份聲明，表明你善意地相信該使用未經你、你的代理人或法律授權；</li>
          <li>一份聲明，表明你通知中的資訊準確無誤，並在偽證罪處罰的前提下聲明你是版權所有人或有權代表版權所有人行事；</li>
          <li>你的親筆簽名或電子簽名（輸入你的全名即可）。</li>
        </ol>
        <p>我們會刪除相關內容，通知發布者，並向其提供通知的副本。明知虛假而提出主張的人，可能需要承擔損害賠償責任。</p>
      </section>

      <section>
        <h2>如果你的漁獲被刪除</h2>
        <p>
          如果你認為內容是被誤刪的，或你有權發布該內容，請向同一地址傳送反通知，內容包括：被刪除內容的連結；一份在偽證罪處罰的前提下作出的聲明，表明你善意地相信該內容是因錯誤或誤認而被刪除；你的姓名、地址和電話號碼；你同意接受你所在地址對應的聯邦法院（如在美國境外，則為 FishEye 所在的任何法院）的管轄，並同意接受發出通知者的文書送達；以及你的簽名。除非投訴人在 10 個工作日內告知我們其已向法院起訴，否則我們可能會恢復該內容。
        </p>
      </section>

      <section>
        <h2>屢次侵權者</h2>
        <p>
          對於屢次發布侵犯他人版權內容的使用者，我們會關閉其帳戶。另請參閱<Link href="/terms">使用條款</Link>。
        </p>
      </section>
    </>
  );
}

export const zht: LegalText = {
  title: "版權與內容",
  lede: "如何告訴我們某條漁獲違反了規則，或某張照片、某段文字未經權利人許可被髮布。",
  description: "如何舉報違反規則的漁獲，或侵犯你版權的內容。",
  Body,
};
