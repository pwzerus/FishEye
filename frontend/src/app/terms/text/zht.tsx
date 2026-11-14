// 由 zh.tsx 自動產生（frontend/scripts/zh_hant.py，OpenCC s2twp）。
// Generated from zh.tsx by scripts/zh_hant.py: edit zh.tsx and run it again, not this file.
import Link from "next/link";

import { LEGAL, legalDate } from "@/lib/legal";

import { Contents, Heading, sec, type SectionTitles, type TermsText } from "./shared";

// 使用條款的簡體中文譯文，逐條對應 en.tsx；以英文版為準（見「一般條款」）。
// 改 en.tsx 時同步改這裡，然後在 frontend/ 下執行 scripts/zh_hant.py 生成繁體版。

const TITLES: SectionTitles = {
  agreeing: "接受本條款",
  accounts: "誰可以使用 FishEye",
  information: "釣魚資訊是參考，不是法規",
  "ai-answers": "AI 回答",
  plus: "FishEye Plus",
  "your-content": "你分享的內容",
  rules: "使用規則",
  moderation: "內容管理與關閉帳戶",
  "our-content": "FishEye 自己的內容",
  "third-parties": "第三方的資料、服務和連結",
  copyright: "版權投訴",
  safety: "你的安全由你負責",
  disclaimers: "不作保證",
  liability: "我們的責任限制",
  release: "免除責任",
  indemnity: "因你引起的索賠",
  disputes: "爭議與仲裁",
  changes: "變更",
  "app-stores": "通過 App Store 或 Google Play 獲取的應用",
  general: "一般條款",
  contact: "聯絡方式",
};

const day = (iso: string) => legalDate(iso, "zh-CN");
// LEGAL.governingState（Texas）的中文名。
const STATE = "德克薩斯州";

function Body() {
  const optOut = LEGAL.optOutDays;
  return (
    <>
      <section className="legal-summary" aria-labelledby="short-version">
        <h2 id="short-version">要點</h2>
        <ul>
          <li>
            <strong>FishEye 是參考工具。</strong>法規、通行資訊、魚類資料、預報和 AI 回答都可能出錯。以你所在州的現行法規和水邊的告示為準。
          </li>
          <li>
            <strong>釣魚有風險。</strong>在哪裡、什麼時候、怎樣釣魚由你決定，相關風險也由你承擔。
          </li>
          <li>
            <strong>AI 回答來自 AI，不是真人。</strong>回答可能出錯，涉及重要事項時請自行核實。
          </li>
          <li>
            <strong>你發布的內容歸你所有。</strong>你允許 FishEye 展示這些內容，並對其負責。
          </li>
          <li>
            <strong>FishEye Plus 會自動續訂，直到你取消</strong>，你可以隨時取消。
          </li>
          <li>
            <strong>爭議通過個人仲裁或小額訴訟法院解決</strong>，不適用集體訴訟，除非你在 {optOut} 天內選擇退出。
          </li>
        </ul>
        <p className="legal-note">這份摘要幫助你快速瞭解要點，具有約束力的是下面的完整條款。</p>
      </section>

      <Contents label="目錄" titles={TITLES} />

      <section id="agreeing">
        <Heading id="agreeing" titles={TITLES} />
        <p>
          本使用條款（「本條款」）是你與 {LEGAL.operator || "FishEye 的運營者"}（「FishEye」或「我們」）之間的協議。本條款適用於{" "}
          {LEGAL.site} 網站、FishEye 應用以及其中的全部內容，包括地圖、魚類指南、問答及其 AI
          回答、拍照識別、漁獲、評論和帳戶（統稱「FishEye」）。我們的<Link href="/privacy">隱私政策</Link>和
          <Link href="/copyright">版權頁面</Link>是本條款的組成部分。
        </p>
        <p>
          你在建立帳戶、開通 FishEye Plus 或使用 FishEye 時，即表示接受本條款。如果你不同意，請不要使用 FishEye。如果你在{" "}
          {day(LEGAL.updatedIso)}之前已有帳戶，本條款自 {day(LEGAL.existingUsersFromIso)}
          起對你適用；在此之前，仍適用此前的條款。如果你代表某個組織使用 FishEye，你也代表該組織接受本條款，並確認你有權這樣做。
        </p>
        <p className="legal-conspicuous">
          請閱讀第 {sec("disputes")} 條。該條規定，你與 FishEye
          之間的爭議通過具有約束力的個人仲裁或在小額訴訟法院解決，不適用集體訴訟，也不由陪審團審理，除非你在首次接受本條款後的{" "}
          {optOut} 天內選擇退出。
        </p>
      </section>

      <section id="accounts">
        <Heading id="accounts" titles={TITLES} />
        <ul>
          <li>
            任何人都可以瀏覽地圖和指南。建立帳戶須年滿 {LEGAL.minimumAge} 歲。未滿 {LEGAL.minimumAge} 歲的人不得建立帳戶。
          </li>
          <li>
            如果你未滿 18
            歲，或未達到你所在地的法定成年年齡，須徵得父母或監護人的同意。父母或監護人表示同意，即代表你接受本條款，並對你使用 FishEye
            的行為（包括任何購買）負責。
          </li>
          <li>
            請提供真實資訊，並及時更新。每人只能擁有一個帳戶：不得另建帳戶，例如為了獲得更多免費 AI 回答或拍照識別次數。
          </li>
          <li>請妥善保管你的密碼。你對帳戶中發生的一切負責。如果你認為有人在使用你的帳戶，請立即告知我們。</li>
          <li>
            你確認自己不在美國政府的禁止或限制交易方名單上，也不位於受美國禁運或被美國認定為支援恐怖主義的國家或地區。
          </li>
          <li>FishEye 是為在美國釣魚而設計的。如果你在其他地方使用，須自行負責，並遵守當地法律。</li>
        </ul>
      </section>

      <section id="information">
        <Heading id="information" titles={TITLES} />
        <p>
          FishEye
          彙集了公開資料、自有指南、其他釣友的漁獲和計算機估算。我們盡力保證內容正確，但無法保證其準確、完整、及時，或適用於你所在的水域。請用它來做計劃，出發前再核實。
        </p>
        <ul>
          <li>
            <strong>法規和執照。</strong>釣魚執照、季節、尺寸和數量限制、餌料規定和禁釣措施會變化，並且因州、因水域而異。FishEye
            的摘要可能過時或不完整，也不構成法律意見。以你所在州魚類與野生動物管理機構的現行法規和水邊的告示為準。持有正確的執照並遵守法規是你的責任。
          </li>
          <li>
            <strong>通行與土地。</strong>FishEye 上的湖泊、下水坡道、岸邊或釣點可能屬於私人所有、已關閉、不安全，或與地圖顯示的位置不符。FishEye
            不是土地測量，也不說明土地歸誰所有；顯示為公共或未標明私人的地方，仍可能是私人土地。請遵守現場告示，在私人土地上釣魚前先獲得許可，不要擅自進入。
          </li>
          <li>
            <strong>魚類與湖泊資訊。</strong>湖中有哪些魚、放流、水深等資訊來自公開資料和釣友的報告，可能有誤或已過時。
          </li>
          <li>
            <strong>不可用於導航。</strong>FishEye 的地圖和位置可能有偏差，不是航行圖：不要依據它們駕船或辨認方向，請自行留意危險。
          </li>
          <li>
            <strong>天氣、水情和預報。</strong>
            天氣、水位、釣魚指數和最佳時段是根據其他服務的資料和簡單模型得出的估算。情況變化很快，你所在位置的情況也可能不同。
          </li>
          <li>
            <strong>拍照識別。</strong>識別照片中的魚或裝備只是計算機的推測。不要據此判斷一條魚能否合法帶走、是否受保護，或能否安全接觸或食用。
          </li>
          <li>
            <strong>食用魚。</strong>某處水域的魚能否安全食用，取決於當地的魚類食用建議。食用漁獲前，請檢視你所在州的相關建議。
          </li>
          <li>
            <strong>裝備。</strong>指南中提到的裝備只是示例，不代表推薦。FishEye
            不銷售裝備；請按製造商的說明使用。如果今後某個連結會為 FishEye 帶來佣金，我們會在連結旁註明。
          </li>
          <li>
            <strong>不構成專業意見。</strong>FishEye 上的任何內容都不構成法律、醫療、安全或其他專業意見。
          </li>
        </ul>
      </section>

      <section id="ai-answers">
        <Heading id="ai-answers" titles={TITLES} />
        <p>問答可以為你提供由 AI 模型撰寫的回答。它是 AI，不是真人，FishEye 會明確標註。</p>
        <ul>
          <li>
            如果 FishEye
            的指南涵蓋你的問題，它會依據指南迴答；如果指南未涵蓋，則依據模型自身的通用知識回答。這些知識未經 FishEye
            核實。回答可能錯誤、不完整、過時，或不適用於你所在的水域、州或季節，而且 AI 看不到你所在地的實際情況。
          </li>
          <li className="legal-conspicuous">
            使用 AI 回答的風險由你自行承擔。凡涉及你的安全、健康或法律的事項，不要依賴 AI
            回答，並請自行判斷其建議是否安全、是否適合你的水平。有關法規、執照和限制，請以你所在州的魚類與野生動物管理機構為準。
          </li>
          <li>如果你未滿 18 歲，請在父母或監護人的參與下使用 AI 回答。</li>
          <li>請向 AI 詢問與釣魚有關的問題。不得利用它製作有害、違法或冒犯性內容，規避其限制，或批次收集回答。</li>
          <li>
            為了撰寫回答，你的問題以及與之匹配的指南段落會發送給我們的 AI 服務提供商
            Anthropic。不要在問題中填寫個人資訊，無論是你自己的還是他人的。詳見<Link href="/privacy">隱私政策</Link>。
          </li>
          <li>
            免費帳戶每天可獲得一定次數的 AI 回答，次數顯示在按鈕旁。FishEye Plus 在個人使用範圍內不設每日上限；如果某個帳戶的使用看起來屬於自動化或濫用行為，我們可能限制或暫停其
            AI 回答。
          </li>
          <li>
            AI 回答有時可能無法使用，例如我們的服務提供商出現故障，或 FishEye 暫停了該功能。我們可以隨時更改、限制或停止 AI 回答。
          </li>
          <li>
            你可以將獲得的回答用於自己的釣魚活動。如需分享，請先核實，並註明來自 AI。其他人提出相同的問題，可能會得到相同或類似的回答。
          </li>
        </ul>
      </section>

      <section id="plus">
        <Heading id="plus" titles={TITLES} />
        <p>
          FishEye Plus 是一項會員服務。其具體內容以開通時的說明為準；目前，它取消了 AI 回答的每日次數限制。FishEye 也可能向部分帳戶免費提供
          Plus。
        </p>
        <ul>
          <li>
            <strong>付款前</strong>
            ，你會看到價格、扣費週期、自動續訂的說明以及取消方式。完成購買即表示你授權該筆扣費以及此後每次續訂的扣費，直到你取消。
          </li>
          <li>
            <strong>續訂。</strong>Plus 會在每個週期結束時按當時的價格自動續訂，直到你取消。年度會員續訂前，我們會提醒你價格和取消方式。
          </li>
          <li>
            <strong>取消。</strong>你可以隨時取消：如果是在應用內購買的 Plus，請在 Apple 或 Google
            帳戶設定中取消（刪除應用不會取消訂閱）；如果是在網站上購買的，請在<Link href="/account">帳戶頁面</Link>
            取消。取消後不再續訂；在已付費的週期結束前，你仍可使用 Plus。
          </li>
          <li>
            <strong>免費試用。</strong>如果你開始免費試用，試用結束時將自動轉為付費會員，除非你在此之前取消。開始試用時，我們會告訴你具體日期。
          </li>
          <li>
            <strong>價格變動。</strong>我們可能調整 Plus 的價格。新價格對你適用之前，我們會通知你，並留出取消的時間。
          </li>
          <li>
            <strong>退款。</strong>除法律另有規定或我們另有說明外，已付款項不予退還，未用完的週期也不予退款。通過 Apple 或 Google
            購買的，只能按照其政策退款；請向其申請。
          </li>
          <li>
            <strong>如果我們停止提供 Plus</strong>，或在你沒有違反本條款的情況下關閉你的帳戶，我們會退還已付費週期中未使用部分的費用。
          </li>
          <li>
            <strong>免費獲得的 Plus</strong> 在說明的期限內有效，沒有現金價值，也不能轉讓。
          </li>
          <li>價格可能不含稅。適用的稅費由你承擔。</li>
        </ul>
      </section>

      <section id="your-content">
        <Heading id="your-content" titles={TITLES} />
        <p>
          你發布的漁獲、照片、筆記和評論，所有權歸你。為了讓 FishEye 正常運作，你授予 FishEye
          一項全球範圍、非獨佔、免版稅的許可，允許其在 FishEye
          中儲存、複製（例如生成照片的縮小版本或備份）和展示這些內容：公開的漁獲或評論向所有人展示，私密的只向你（和管理員）展示。該許可在你刪除相關內容或帳戶時終止；備份中的副本除外，這些副本會隨時間被替換。
        </p>
        <ul>
          <li>
            你對自己發布的內容負責。只發布你拍攝的或有權使用的照片；未經他人同意，不要發布他人的照片，也不要發布任何人的個人資訊。
          </li>
          <li>
            發布漁獲時，你可以選擇誰能看到它以及位置的精確程度。照片本身仍可能暴露地點，發布前請想清楚。不要發布會讓人進入私人土地的釣點。
          </li>
          <li>
            內容發布前，我們不會逐一審核，也不為其他釣友發布的內容背書。他們的漁獲和評論由他們負責，可能有誤。我們也不核實其他釣友的身份：與只在
            FishEye 上認識的人見面前，請保持基本的警惕。
          </li>
          <li>如果你向我們提出想法或意見回饋，我們可以自由使用，無需向你付費，也不對你承擔任何義務。</li>
        </ul>
      </section>

      <section id="rules">
        <Heading id="rules" titles={TITLES} />
        <p>不得利用 FishEye：</p>
        <ul>
          <li>違反法律，包括有關釣魚、野生動物、划船和擅自闖入的法律，或展示自己、鼓勵他人從事這類行為；</li>
          <li>騷擾、威脅、跟蹤或冒充任何人，或發布他人的個人資訊；</li>
          <li>
            使用侮辱性稱呼，或因種族、民族、國籍、宗教、性別、性取向、性別認同、年齡或殘疾而攻擊他人（含有侮辱性稱呼的名稱和漁獲不予接受）；
          </li>
          <li>
            發布垃圾資訊、廣告、色情內容、無端的暴力或血腥內容，或任何你無權發布的內容。任何將未成年人性化的內容都會被刪除，並報告有關當局；
          </li>
          <li>標註誤導他人的地點，或未經許可引導他人進入私人土地；</li>
          <li>使用機器人或爬蟲從 FishEye 收集資料，批次複製其指南或資料，將其用於訓練 AI 模型，或藉此建立競爭性服務；</li>
          <li>另建帳戶、共享或出售帳戶，或規避 FishEye 的限制、封禁或安全措施；</li>
          <li>探測、破壞 FishEye 的系統或使其過載，上傳惡意軟體，或在法律允許的範圍之外對 FishEye 進行反向工程；</li>
          <li>試圖讓 AI 生成有害內容或無視其指令。</li>
        </ul>
      </section>

      <section id="moderation">
        <Heading id="moderation" titles={TITLES} />
        <ul>
          <li>
            任何擁有帳戶的人都可以舉報公開的漁獲或評論。對於違反本條款的內容和帳戶，或在法律要求、為保護他人或 FishEye
            時，管理員可以隱藏或刪除內容、限制功能，或暫停、關閉帳戶。除非法律或他人安全不允許，我們通常會說明原因。如果你認為我們處理有誤，請寫信給我們。
          </li>
          <li>
            你可以隨時在<Link href="/account">帳戶頁面</Link>刪除帳戶。刪除帳戶不會取消通過 Apple 或 Google 購買的
            Plus；請在相應平臺取消。
          </li>
          <li>
            帳戶關閉後，第 {sec("your-content")} 條（在內容被刪除前，你對所分享內容授予的許可）以及第 {sec("our-content")}{" "}
            條至第 {sec("general")} 條仍然有效。
          </li>
        </ul>
      </section>

      <section id="our-content">
        <Heading id="our-content" titles={TITLES} />
        <p>
          FishEye 的指南、文字、設計、程式碼、名稱和標誌，以及資料的編排方式，歸 FishEye
          或向我們授權的人所有。我們授予你一項個人、非商業、不可轉讓的許可，允許你按照本條款使用
          FishEye；如果你違反本條款，該許可即告終止。歡迎自由分享連結，也可以在註明出處的前提下少量引用；但不得批次複製指南或資料、出售它們，或將其冒充為自己的作品。
        </p>
      </section>

      <section id="third-parties">
        <Heading id="third-parties" titles={TITLES} />
        <ul>
          <li>
            FishEye 使用來自政府機構和開放專案的公開資料，並在資料出現的位置和<Link href="/sources">來源</Link>
            頁面註明出處。地圖資料 © OpenStreetMap 貢獻者；地圖來自 MapTiler；魚類照片來自 Wikimedia
            Commons，各有其許可。上述資料適用其各自的許可和條款。
          </li>
          <li>指向政府機構網站和其他網站的連結僅為方便你使用。我們無法控制這些網站，也不對其負責。</li>
          <li>
            你與 FishEye 一起使用的服務，例如「使用 Google 登入」、Apple 的 App Store、Google Play
            以及你的行動數據套餐，各有其條款。使用 FishEye 時，你必須遵守這些條款。
          </li>
        </ul>
      </section>

      <section id="copyright">
        <Heading id="copyright" titles={TITLES} />
        <p>
          如需舉報侵犯你版權的內容，或回應針對你內容的舉報，請參閱<Link href="/copyright">版權與內容</Link>
          頁面。對於屢次侵權的使用者，我們會關閉其帳戶。
        </p>
      </section>

      <section id="safety">
        <Heading id="safety" titles={TITLES} />
        <p>
          釣魚、划船、涉水、冰釣以及前往水邊都存在實際風險，包括溺水、冷水、失溫、跌倒、雷擊、高溫、魚鉤和刀具、野生動物以及道路事故。FishEye
          看不到你所在地的實際情況。
        </p>
        <ul>
          <li>是否出行、去哪裡、何時去、怎樣去，完全由你決定；你對自身安全以及同行者（尤其是兒童）的安全負責。</li>
          <li>
            出發前檢視天氣和水情，並把行程告訴他人；乘船以及靠近深水或急流時穿好救生衣；不確定冰面是否安全時，不要上冰。
          </li>
          <li>FishEye 不是緊急救援服務。遇到緊急情況，請撥打 911。</li>
        </ul>
        <p className="legal-conspicuous">
          在法律允許的最大範圍內，你承擔你的釣魚、划船、出行及其他活動的全部風險，包括無法預見的風險，以及因依賴 FishEye
          而產生的任何風險。
        </p>
      </section>

      <section id="disclaimers">
        <Heading id="disclaimers" titles={TITLES} />
        <p className="legal-conspicuous">
          FishEye 按「現狀」和「現有可用狀態」提供。在法律允許的最大範圍內，FishEye 不對 FishEye
          或其中的任何內容（包括其資訊、地圖、預報、AI
          回答、拍照識別和他人發布的內容）作出任何明示或默示的承諾或保證。這包括對其準確、完整、及時、可靠、安全、可用、不中斷或無錯誤的任何承諾，以及對適銷性、特定用途適用性、所有權和不侵權的默示保證。
        </p>
        <p>有些地方不允許排除其中部分保證。在這些地方，上述排除在法律允許的範圍內適用。</p>
      </section>

      <section id="liability">
        <Heading id="liability" titles={TITLES} />
        <p>在本條款中，「FishEye 相關方」是指 FishEye、其運營者，以及參與 FishEye 工作或為其工作的人員。</p>
        <div className="legal-conspicuous">
          <p>在法律允許的最大範圍內：</p>
          <ul>
            <li>
              FishEye
              相關方不對間接、附帶、特殊、後果性、懲戒性或懲罰性損害賠償，或利潤、資料或商譽的損失承擔責任，即使已被告知可能發生此類損害；
            </li>
            <li>
              對於你在釣魚、划船或出行時發生的任何事情，在你通過 FishEye 找到的地點發生的任何事情，罰款或處罰，以及你根據 FishEye 的資訊或 AI
              回答作出的決定，FishEye 相關方均不承擔責任；
            </li>
            <li>
              就所有與 FishEye 或本條款有關的索賠，FishEye 相關方的總責任以 {LEGAL.liabilityFloorUsd} 美元與索賠發生前 12
              個月內你向 FishEye 支付的金額兩者中的較高者為限。
            </li>
          </ul>
          <p>無論依據何種法律理論（合同、保證、過失、嚴格責任或其他），上述限制均適用。</p>
        </div>
        <p>
          上述限制不限制因重大過失、故意不當行為或欺詐而產生的責任，也不限制法律不允許限制的任何責任。有些地方不允許這些限制，因此其中部分可能不適用於你。
        </p>
      </section>

      <section id="release">
        <Heading id="release" titles={TITLES} />
        <p className="legal-conspicuous">
          在法律允許的最大範圍內，對於因你的釣魚、划船、出行或其他活動，因依賴 FishEye 上的資訊、地圖、預報或 AI
          回答，或因你與其他釣友或任何其他人（例如土地所有者）之間的爭議而造成的人身傷害、死亡、財產損失或其他損失，你免除
          FishEye 相關方的一切已知或未知的索賠責任，包括基於 FishEye
          相關方過失的索賠，並承諾不就此類索賠起訴他們。本免責不涵蓋重大過失或故意不當行為。
        </p>
        <p>
          如果你居住在加利福尼亞州，你放棄《加利福尼亞州民法典》第 1542
          條賦予的權利。該條規定：「概括性免責不適用於債權人或免責方在簽署免責書時不知道或未懷疑存在的、對其有利的索賠；若其知道這些索賠，將會對其與債務人或被免責方的和解產生重大影響。」你同樣放棄其他地方任何類似法律賦予的權利。
        </p>
      </section>

      <section id="indemnity">
        <Heading id="indemnity" titles={TITLES} />
        <p>
          在法律允許的範圍內，對於他人因你發布的內容、你違反本條款或法律，或你的釣魚或其他活動（例如在你標註的釣點擅自闖入）而提出的索賠，以及由此產生的損失、費用和合理的律師費，你將為
          FishEye 相關方進行抗辯並予以賠償。我們會將此類索賠告知你，可以選擇自行負責抗辯，你應在合理需要的範圍內提供協助。
        </p>
      </section>

      <section id="disputes">
        <Heading id="disputes" titles={TITLES} />
        <p className="legal-conspicuous">請仔細閱讀本條。它影響你的權利，包括向法院起訴的權利。</p>
        <p>
          <strong>先與我們溝通。</strong>大多數問題都可以通過溝通解決。在啟動仲裁或訴訟之前，請傳送通知至{" "}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
          ，郵件主題為「Dispute」（爭議），寫明你的姓名、帳戶電子郵件、事情經過以及你的訴求。我們會將我們的通知傳送到你的帳戶電子郵件。隨後雙方在
          60 天內本著誠意嘗試解決；在此期間，該索賠的任何時效均暫停計算。
        </p>
        <p>
          <strong>仲裁。</strong>如果爭議未能解決，你與 FishEye 同意，因本條款或 FishEye
          引起或與之相關的任何爭議或索賠（「索賠」），均由一名仲裁員以個人名義進行具有約束力的仲裁裁決，而不通過法院解決，但以下情況除外：
        </p>
        <ul>
          <li>任何一方均可在符合條件時，向小額訴訟法院提起個人索賠；</li>
          <li>任何一方均可請求法院制止對其智慧財產權的侵犯或濫用；</li>
          <li>如果你按下文所述選擇退出，本段不適用。</li>
        </ul>
        <p>
          本條受《聯邦仲裁法》管轄。仲裁由美國仲裁協會（AAA）依照其《消費者仲裁規則》進行，適用時依照其大規模仲裁規則（見
          adr.org）。仲裁員可以裁決給予你與法院相同的個人救濟。對於你提起的索賠，FishEye 承擔 AAA
          的立案費、管理費和仲裁員費用中超出你向法院起訴所需費用的部分，除非仲裁員認定你的索賠屬於無理索賠。任何聽證均以視訊或電話方式進行；如果你願意，也可以在你居住的縣當面進行。
        </p>
        <p className="legal-conspicuous">
          不適用集體訴訟。你與 FishEye
          只能以個人名義相互提出索賠，不得作為任何集體、群體、合併或代表訴訟程序的原告或成員。如果本句對某項索賠被認定為不可執行，該索賠應提交法院而非仲裁。如果法律不允許將公共禁令救濟的請求提交仲裁，該請求在個人仲裁結束後提交法院。如果索賠提交法院，在法律允許的範圍內，你與
          FishEye 均放棄陪審團審理。
        </p>
        <p>
          <strong>選擇退出。</strong>你可以在首次接受本條款後的 {optOut} 天內選擇退出仲裁：傳送郵件至{" "}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
          ，郵件主題為「Arbitration opt-out」（退出仲裁），並寫明你的姓名和帳戶電子郵件。選擇退出不會改變本條款的其他任何內容。
        </p>
        <p>
          <strong>本條的變更。</strong>本條的變更不適用於任何一方已發出通知的索賠。如果我們作出重要變更，你可以在 30
          天內發郵件拒絕該變更，此前的版本將繼續對你適用。
        </p>
        <p>
          <strong>時效。</strong>在法律允許的範圍內，索賠必須在其發生後兩年內提起，否則不得再提起。
        </p>
        <p>
          <strong>適用法律和法院。</strong>本條款受{STATE}法律管轄，不考慮法律衝突規則；本條同時受《聯邦仲裁法》管轄。未經仲裁的索賠應提交位於
          {STATE}的州法院或聯邦法院，你與 FishEye 同意接受其管轄，除非你居住地的法律賦予你在當地提起訴訟的權利。
        </p>
      </section>

      <section id="changes">
        <Heading id="changes" titles={TITLES} />
        <ul>
          <li>
            我們可能更改 FishEye、增加或移除功能，或停止提供 FishEye。如果我們停止提供你已付費的服務，第 {sec("plus")}{" "}
            條說明了你可以獲得的退款。
          </li>
          <li>
            我們可能修改本條款。我們會更新頁首的日期；對於重要變更，我們會在變更生效至少 {LEGAL.noticeDays}{" "}
            天前通過網站或電子郵件通知你，除非法律要求更早變更，或變更涉及新功能。變更生效後你繼續使用
            FishEye，即表示接受變更。如果你不接受，請停止使用 FishEye 並刪除帳戶。
          </li>
          <li>標註為新功能或測試功能的部分，出錯的可能性高於其他部分，並且可能會變更或下線。</li>
        </ul>
      </section>

      <section id="app-stores">
        <Heading id="app-stores" titles={TITLES} />
        <p>如果你是從 Apple 的 App Store 獲取的 FishEye 應用：</p>
        <ul>
          <li>本條款僅存在於你與 FishEye 之間，而非你與 Apple 之間。對應用及其內容負責的是 FishEye，而不是 Apple。</li>
          <li>
            你對應用的許可不可轉讓，並且僅限於在你擁有或控制的 Apple 品牌產品上使用，具體以
            Apple《媒體服務條款與條件》中的《使用規則》（包括「家人共享」）允許的範圍為準。本條款與該《使用規則》衝突時，就該應用而言，以《使用規則》為準。
          </li>
          <li>應用的維護和支援由 FishEye 而非 Apple 提供。Apple 沒有提供維護和支援的義務。</li>
          <li>
            如果應用不符合任何適用的保證，你可以通知 Apple，Apple 將退還該應用的購買價款（如有）。在法律允許的範圍內，Apple
            對該應用不承擔其他任何保證義務；因此類不符合而產生的任何其他索賠、損失或費用，在本條款未予排除的範圍內，由 FishEye 負責。
          </li>
          <li>
            與應用或你使用應用有關的任何索賠，包括產品責任索賠、關於應用不符合法律或監管要求的索賠，以及依據消費者保護、隱私或類似法律提出的索賠，均由
            FishEye 而非 Apple 負責。
          </li>
          <li>
            如果有人聲稱應用或你對應用的使用侵犯了其智慧財產權，由 FishEye 而非 Apple 負責調查、抗辯、和解和了結該索賠。
          </li>
          <li>Apple 及其子公司是本條款的第三方受益人。你接受本條款後，Apple 有權對你執行本條款。</li>
        </ul>
        <p>如果你是從 Google Play 獲取的應用，你的購買受 Google 的條款約束，Google 不對該應用負責。</p>
      </section>

      <section id="general">
        <Heading id="general" titles={TITLES} />
        <ul>
          <li>本條款、隱私政策、版權頁面以及針對特定功能顯示的任何條款，構成你與 FishEye 之間關於 FishEye 的完整協議。</li>
          <li>
            如果本條款的某一部分無法執行，該部分將在使其可執行所需的最小範圍內予以修改，其餘部分仍然有效。我們未執行某一部分，並不代表我們放棄該部分。
          </li>
          <li>你不得轉讓本條款或你的帳戶。我們可以轉讓，例如轉讓給接手運營 FishEye 的公司，或在合併、出售時轉讓。</li>
          <li>對於因超出我們合理控制範圍的事件造成的延誤或未能履行，我們不承擔責任。</li>
          <li>
            本條款並不使你與 FishEye 成為合夥人、僱主與僱員或彼此的代理人。除 FishEye 相關方（第 {sec("liability")}{" "}
            條至第 {sec("indemnity")} 條）和 Apple（第 {sec("app-stores")} 條）外，任何其他人均無權執行本條款。
          </li>
          <li>
            我們可以通過傳送到你帳戶電子郵件的電子郵件或在 FishEye
            上向你傳送通知；你同意電子形式的通知和協議與書面形式具有同等效力。你可以按下方聯絡方式向我們傳送通知。
          </li>
          <li>本條款以英文撰寫。任何譯文僅為方便閱讀而提供，以英文版本為準。「包括」指「包括但不限於」。</li>
          <li>
            加利福尼亞州居民：可以書面形式聯絡加利福尼亞州消費者事務部消費者服務處投訴協助組，地址為 1625 North Market Blvd., Suite N
            112, Sacramento, CA 95834，或致電 (800) 952-5210。
          </li>
        </ul>
      </section>

      <section id="contact">
        <Heading id="contact" titles={TITLES} />
        <p>
          {LEGAL.operator && (
            <>
              {LEGAL.operator}
              <br />
            </>
          )}
          {LEGAL.mailingAddress && (
            <>
              {LEGAL.mailingAddress}
              <br />
            </>
          )}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
        </p>
        <p>有關 FishEye 或應用的問題、投訴和索賠，請傳送至此電子郵件。</p>
      </section>
    </>
  );
}

export const zht: TermsText = {
  title: "使用條款",
  lede: "這是你與 FishEye 之間的協議。請仔細閱讀：它要求你為自身安全負責，限制了 FishEye 承擔的責任，並規定大多數爭議通過個人仲裁解決。",
  description: "使用 FishEye 的協議：釣魚資訊、AI 回答、FishEye Plus、你分享的內容以及爭議解決。",
  Body,
};
