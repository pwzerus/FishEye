// 由 zh.tsx 自動產生（frontend/scripts/zh_hant.py，OpenCC s2twp）。
// Generated from zh.tsx by scripts/zh_hant.py: edit zh.tsx and run it again, not this file.
import Link from "next/link";

import { LEGAL, type LegalText } from "@/lib/legal";

// 隱私政策的簡體中文譯文，逐節對應 en.tsx；以英文版為準。
// 改 en.tsx 時同步改這裡，然後在 frontend/ 下執行 scripts/zh_hant.py 生成繁體版。
// 每段寫在一行裡：JSX 會把換行變成空格。

function Body() {
  return (
    <>
      <section>
        <h2>我們是誰</h2>
        <p>
          FishEye（{LEGAL.site}）{LEGAL.operator ? `由 ${LEGAL.operator} ` : ""}在美國運營。有關本政策或你的資料的問題，請傳送至 <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>。
        </p>
      </section>

      <section>
        <h2>我們收集哪些資訊</h2>
        <p>無需帳戶，你也可以使用地圖、魚類指南、問答、拍照識別（每天幾張）和意見回饋功能。我們儲存的資訊如下：</p>
        <ul>
          <li>
            <strong>你的帳戶：</strong>你的電子郵件地址和顯示名稱，以及你的密碼。密碼只以 scrypt 雜湊值儲存，我們無法還原。如果你使用 Google 登入，Google 會告訴我們你的電子郵件地址和一個帳戶 ID；我們永遠看不到你的 Google 密碼。我們會記錄你的註冊時間和最近一次登入時間。
          </li>
          <li>
            <strong>你的登入會話：</strong>一個 Cookie 儲存一個隨機令牌（我們只儲存其雜湊值），同時記錄該會話最近一次使用的時間，以及你的瀏覽器名稱和版本。
          </li>
          <li>
            <strong>你分享的漁獲：</strong>你放置標記的位置、標題、筆記、魚種、日期和照片。每張照片在儲存前，我們都會重新儲存，並去除其中的隱藏資料，包括 GPS 位置和相機資訊。
          </li>
          <li>
            <strong>舉報與審核：</strong>你對漁獲或評論提交的舉報，以及管理員操作的記錄。
          </li>
          <li>
            <strong>AI 回答和 Plus：</strong>你每天使用的 AI 回答次數（用於計算每日額度），以及你的帳戶是否開通了 FishEye Plus、有效期到何時。每日次數以由你的電子郵件地址生成的單向代碼儲存，而不是儲存電子郵件地址本身。
          </li>
          <li>
            <strong>點贊和評論：</strong>你點贊過哪些漁獲，以及你寫的評論。評論和漁獲的點贊數是公開的。你分享的公開漁獲還會讓你的名字出現在排行榜上，除非你在帳戶頁面關閉此功能。
          </li>
          <li>
            <strong>漁獲提醒（如果你設定了）：</strong>魚種、地點（精確到約 1 公里）、距離和你的語言，以便我們給你傳送郵件。每封郵件都附有退訂連結，提醒會隨你的帳戶一起刪除。
          </li>
          <li>
            <strong>你傳送的意見回饋：</strong>你的留言、你當時所在的頁面和你的語言。登入時，意見回饋與你的帳戶一起儲存，以便我們回覆；如果你刪除帳戶，我們會保留留言，但不再顯示傳送者。未登入時，意見回饋不關聯任何帳戶；只有你為了獲得回覆而留下電子郵件地址時，才會一併儲存該地址。
          </li>
          <li>
            <strong>問答無法回答的問題：</strong>問題本身、問題的語言，以及你選擇的州或魚種，以便我們知道接下來該編寫哪些指南。我們不記錄提問者，會先刪除其中的電子郵件地址、電話號碼和連結，並在 90 天后刪除這些問題。
          </li>
          <li>
            <strong>訪問次數：</strong>每個頁面每天被開啟的次數，以及連結到我們的網站（只記錄網站名稱，例如 reddit.com）或連結中的標記（例如 ?ref=reddit）。僅此而已：不記錄 IP 地址，不使用 Cookie 或其他識別符號，也沒有任何能區分訪客或跨頁面追蹤他人的資訊。我們用它來了解是否有人找到 FishEye，以及從哪裡找到。
          </li>
          <li>
            <strong>伺服器日誌：</strong>和大多數網站一樣，我們的伺服器會記錄每個請求（IP 地址、頁面、時間、瀏覽器），以保障網站正常運作和安全。這些記錄只在所需期限內儲存。為防止濫用，伺服器還會在記憶體中按 IP 地址統計請求次數（例如未登入時每天的免費拍照識別次數）；這些計數不會寫入儲存，一天內即會清除。
          </li>
        </ul>
      </section>

      <section>
        <h2>你的釣點</h2>
        <p>
          你設為<strong>私密</strong>的漁獲，只有你能看到；在處理舉報或問題需要時，我們的管理員也能看到。<strong>公開</strong>的漁獲所有人都能看到，但預設只顯示到所在的湖泊（不在湖邊時顯示到所在的縣）：確切位置只有你和管理員能看到，除非你選擇向其他釣友顯示「確切的釣點」。你可以隨時更改此設定，或將漁獲設為私密。
        </p>
      </section>

      <section>
        <h2>我們如何使用這些資訊</h2>
        <ul>
          <li>維護你的帳戶，向你展示你的漁獲；如果你設為公開，也向他人展示。</li>
          <li>
            根據照片識別魚或釣魚裝備，並檢查漁獲照片中的魚是否與你填寫的魚種一致。這些都在我們自己的伺服器上完成，單獨識別的照片不會儲存。只有當你就某張照片詢問 AI 時，照片才會傳送給其他公司（見下文的 Anthropic）。
          </li>
          <li>保障 FishEye 的安全：限制垃圾資訊和濫用，處理舉報，並維持服務正常運作。</li>
          <li>在你寫信給我們時回覆你。</li>
        </ul>
        <p>
          我們不出售或出租個人資訊，不為廣告目的共享個人資訊；FishEye 沒有廣告、沒有追蹤 Cookie，也不使用第三方分析服務。上述訪問次數由我們自己統計，不包含任何訪客身份資訊。
        </p>
      </section>

      <section>
        <h2>還有誰會處理這些資訊</h2>
        <ul>
          <li>
            <strong>Amazon Web Services</strong> 在美國託管 FishEye 的伺服器和資料庫。
          </li>
          <li>
            <strong>Anthropic</strong>：當你在問答中詢問 AI 時，你的問題和與之匹配的指南段落，或你詢問的照片，會發送給 Anthropic 的 AI 模型以撰寫回答。照片會先由我們重新儲存，去除位置和相機資訊，我們也不會儲存該照片。你的帳戶資訊不會被髮送。請不要在問題或照片中包含個人資訊。
          </li>
          <li>
            <strong>Google</strong>：僅在你使用「使用 Google 登入」時。
          </li>
          <li>
            <strong>OpenStreetMap 的 Nominatim</strong> 會收到你搜索的地點文字，由我們的伺服器傳送，而不是從你的瀏覽器傳送。
          </li>
          <li>
            你的瀏覽器會直接載入<strong>來自 MapTiler 的地圖圖塊</strong>（MapTiler 不可用時改用 OpenStreetMap）和<strong>來自 Wikimedia Commons 的魚類照片</strong>。和任何網站一樣，它們會收到你的 IP 地址和瀏覽器資訊，並適用其各自的隱私政策。
          </li>
          <li>有關當局：在法律要求或為保護他人安全時。</li>
        </ul>
        <p>
          你使用「附近」功能時，裝置的位置只在你的瀏覽器中使用；為了開啟你附近的漁獲，我們會在伺服器上查詢你所在的縣，但不會儲存或記錄該位置。
        </p>
      </section>

      <section>
        <h2>Cookie 和瀏覽器儲存</h2>
        <p>
          一個 Cookie 用於保持你的登入狀態。你的瀏覽器還會儲存少量偏好設定，例如你為釣魚法規選擇的州。統計訪問次數不使用 Cookie，也不在你的瀏覽器中儲存任何內容。這些都不用於廣告或追蹤。
        </p>
      </section>

      <section>
        <h2>你的選擇</h2>
        <ul>
          <li>編輯或刪除任何漁獲，將其設為私密，或更改誰能看到它的確切位置。</li>
          <li>
            在<Link href="/account">帳戶頁面</Link>刪除你的帳戶。這會刪除你的帳戶、登入會話以及漁獲和照片。你提交的舉報會保留，但不再顯示你的名字，以便管理員完成審核。你已使用的 AI 回答次數會以單向代碼的形式保留最多 30 天，因此刪除帳戶後重新註冊，不會重置免費次數。
          </li>
          <li>
            如需獲取你的資料副本，或更正、刪除你的資料，請傳送郵件至 <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>。我們會在 30 天內回覆。
          </li>
        </ul>
      </section>

      <section>
        <h2>儲存期限</h2>
        <p>儲存到你刪除相關內容或帳戶為止。AI 回答的每日次數會在 30 天后刪除。資料庫備份可能會短期保留副本，之後會被替換。</p>
      </section>

      <section>
        <h2>安全</h2>
        <p>
          網站使用 HTTPS，密碼和會話令牌只以雜湊值儲存，只有 FishEye 的管理員可以訪問伺服器。沒有任何系統是絕對安全的；如果發生影響你的問題，我們會告訴你。
        </p>
      </section>

      <section>
        <h2>兒童</h2>
        <p>
          FishEye 帳戶僅供年滿 {LEGAL.minimumAge} 歲的人使用，未滿 18 歲的人需要徵得父母同意。任何人無需帳戶即可瀏覽地圖和指南。根據《兒童線上隱私保護法》（COPPA），我們不會在知情的情況下收集未滿 {LEGAL.minimumAge} 歲兒童的個人資訊。如果我們得知有未滿 {LEGAL.minimumAge} 歲的兒童建立了帳戶，我們會將其刪除；家長也可以傳送郵件至 <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a> 要求刪除。
        </p>
      </section>

      <section>
        <h2>變更</h2>
        <p>我們修改本政策時，會更新上方的日期；對於重要變更，我們會在其生效前在網站上說明。</p>
      </section>
    </>
  );
}

export const zht: LegalText = {
  title: "隱私政策",
  lede: "FishEye 只收集維護你的帳戶和展示你的漁獲所需的資訊。我們不出售你的資料，不展示廣告，也絕不會把你的釣點透露給他人。",
  description: "FishEye 收集哪些資訊、為什麼收集、還有誰會接觸這些資訊，以及如何刪除。",
  Body,
};
