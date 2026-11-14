import Link from "next/link";

import { LEGAL, legalDate } from "@/lib/legal";

import { Contents, Heading, sec, type SectionTitles, type TermsText } from "./shared";

// 使用条款的简体中文译文，逐条对应 en.tsx；以英文版为准（见“一般条款”）。
// 改 en.tsx 时同步改这里，然后在 frontend/ 下运行 scripts/zh_hant.py 生成繁体版。

const TITLES: SectionTitles = {
  agreeing: "接受本条款",
  accounts: "谁可以使用 FishEye",
  information: "钓鱼信息是参考，不是法规",
  "ai-answers": "AI 回答",
  plus: "FishEye Plus",
  "your-content": "你分享的内容",
  rules: "使用规则",
  moderation: "内容管理与关闭账户",
  "our-content": "FishEye 自己的内容",
  "third-parties": "第三方的数据、服务和链接",
  copyright: "版权投诉",
  safety: "你的安全由你负责",
  disclaimers: "不作保证",
  liability: "我们的责任限制",
  release: "免除责任",
  indemnity: "因你引起的索赔",
  disputes: "争议与仲裁",
  changes: "变更",
  "app-stores": "通过 App Store 或 Google Play 获取的应用",
  general: "一般条款",
  contact: "联系方式",
};

const day = (iso: string) => legalDate(iso, "zh-CN");
// LEGAL.governingState（Texas）的中文名。
const STATE = "得克萨斯州";

function Body() {
  const optOut = LEGAL.optOutDays;
  return (
    <>
      <section className="legal-summary" aria-labelledby="short-version">
        <h2 id="short-version">要点</h2>
        <ul>
          <li>
            <strong>FishEye 是参考工具。</strong>法规、通行信息、鱼类数据、预报和 AI 回答都可能出错。以你所在州的现行法规和水边的告示为准。
          </li>
          <li>
            <strong>钓鱼有风险。</strong>在哪里、什么时候、怎样钓鱼由你决定，相关风险也由你承担。
          </li>
          <li>
            <strong>AI 回答来自 AI，不是真人。</strong>回答可能出错，涉及重要事项时请自行核实。
          </li>
          <li>
            <strong>你发布的内容归你所有。</strong>你允许 FishEye 展示这些内容，并对其负责。
          </li>
          <li>
            <strong>FishEye Plus 会自动续订，直到你取消</strong>，你可以随时取消。
          </li>
          <li>
            <strong>争议通过个人仲裁或小额诉讼法院解决</strong>，不适用集体诉讼，除非你在 {optOut} 天内选择退出。
          </li>
        </ul>
        <p className="legal-note">这份摘要帮助你快速了解要点，具有约束力的是下面的完整条款。</p>
      </section>

      <Contents label="目录" titles={TITLES} />

      <section id="agreeing">
        <Heading id="agreeing" titles={TITLES} />
        <p>
          本使用条款（“本条款”）是你与 {LEGAL.operator || "FishEye 的运营者"}（“FishEye”或“我们”）之间的协议。本条款适用于{" "}
          {LEGAL.site} 网站、FishEye 应用以及其中的全部内容，包括地图、鱼类指南、问答及其 AI
          回答、拍照识别、渔获、评论和账户（统称“FishEye”）。我们的<Link href="/privacy">隐私政策</Link>和
          <Link href="/copyright">版权页面</Link>是本条款的组成部分。
        </p>
        <p>
          你在创建账户、开通 FishEye Plus 或使用 FishEye 时，即表示接受本条款。如果你不同意，请不要使用 FishEye。如果你在{" "}
          {day(LEGAL.updatedIso)}之前已有账户，本条款自 {day(LEGAL.existingUsersFromIso)}
          起对你适用；在此之前，仍适用此前的条款。如果你代表某个组织使用 FishEye，你也代表该组织接受本条款，并确认你有权这样做。
        </p>
        <p className="legal-conspicuous">
          请阅读第 {sec("disputes")} 条。该条规定，你与 FishEye
          之间的争议通过具有约束力的个人仲裁或在小额诉讼法院解决，不适用集体诉讼，也不由陪审团审理，除非你在首次接受本条款后的{" "}
          {optOut} 天内选择退出。
        </p>
      </section>

      <section id="accounts">
        <Heading id="accounts" titles={TITLES} />
        <ul>
          <li>
            任何人都可以浏览地图和指南。创建账户须年满 {LEGAL.minimumAge} 岁。未满 {LEGAL.minimumAge} 岁的人不得创建账户。
          </li>
          <li>
            如果你未满 18
            岁，或未达到你所在地的法定成年年龄，须征得父母或监护人的同意。父母或监护人表示同意，即代表你接受本条款，并对你使用 FishEye
            的行为（包括任何购买）负责。
          </li>
          <li>
            请提供真实信息，并及时更新。每人只能拥有一个账户：不得另建账户，例如为了获得更多免费 AI 回答或拍照识别次数。
          </li>
          <li>请妥善保管你的密码。你对账户中发生的一切负责。如果你认为有人在使用你的账户，请立即告知我们。</li>
          <li>
            你确认自己不在美国政府的禁止或限制交易方名单上，也不位于受美国禁运或被美国认定为支持恐怖主义的国家或地区。
          </li>
          <li>FishEye 是为在美国钓鱼而设计的。如果你在其他地方使用，须自行负责，并遵守当地法律。</li>
        </ul>
      </section>

      <section id="information">
        <Heading id="information" titles={TITLES} />
        <p>
          FishEye
          汇集了公开数据、自有指南、其他钓友的渔获和计算机估算。我们尽力保证内容正确，但无法保证其准确、完整、及时，或适用于你所在的水域。请用它来做计划，出发前再核实。
        </p>
        <ul>
          <li>
            <strong>法规和执照。</strong>钓鱼执照、季节、尺寸和数量限制、饵料规定和禁钓措施会变化，并且因州、因水域而异。FishEye
            的摘要可能过时或不完整，也不构成法律意见。以你所在州鱼类与野生动物管理机构的现行法规和水边的告示为准。持有正确的执照并遵守法规是你的责任。
          </li>
          <li>
            <strong>通行与土地。</strong>FishEye 上的湖泊、下水坡道、岸边或钓点可能属于私人所有、已关闭、不安全，或与地图显示的位置不符。FishEye
            不是土地测量，也不说明土地归谁所有；显示为公共或未标明私人的地方，仍可能是私人土地。请遵守现场告示，在私人土地上钓鱼前先获得许可，不要擅自进入。
          </li>
          <li>
            <strong>鱼类与湖泊信息。</strong>湖中有哪些鱼、放流、水深等信息来自公开资料和钓友的报告，可能有误或已过时。
          </li>
          <li>
            <strong>不可用于导航。</strong>FishEye 的地图和位置可能有偏差，不是航行图：不要依据它们驾船或辨认方向，请自行留意危险。
          </li>
          <li>
            <strong>天气、水情和预报。</strong>
            天气、水位、钓鱼指数和最佳时段是根据其他服务的数据和简单模型得出的估算。情况变化很快，你所在位置的情况也可能不同。
          </li>
          <li>
            <strong>拍照识别。</strong>识别照片中的鱼或装备只是计算机的推测。不要据此判断一条鱼能否合法带走、是否受保护，或能否安全接触或食用。
          </li>
          <li>
            <strong>食用鱼。</strong>某处水域的鱼能否安全食用，取决于当地的鱼类食用建议。食用渔获前，请查看你所在州的相关建议。
          </li>
          <li>
            <strong>装备。</strong>指南中提到的装备只是示例，不代表推荐。FishEye
            不销售装备；请按制造商的说明使用。如果今后某个链接会为 FishEye 带来佣金，我们会在链接旁注明。
          </li>
          <li>
            <strong>不构成专业意见。</strong>FishEye 上的任何内容都不构成法律、医疗、安全或其他专业意见。
          </li>
        </ul>
      </section>

      <section id="ai-answers">
        <Heading id="ai-answers" titles={TITLES} />
        <p>问答可以为你提供由 AI 模型撰写的回答。它是 AI，不是真人，FishEye 会明确标注。</p>
        <ul>
          <li>
            如果 FishEye
            的指南涵盖你的问题，它会依据指南回答；如果指南未涵盖，则依据模型自身的通用知识回答。这些知识未经 FishEye
            核实。回答可能错误、不完整、过时，或不适用于你所在的水域、州或季节，而且 AI 看不到你所在地的实际情况。
          </li>
          <li className="legal-conspicuous">
            使用 AI 回答的风险由你自行承担。凡涉及你的安全、健康或法律的事项，不要依赖 AI
            回答，并请自行判断其建议是否安全、是否适合你的水平。有关法规、执照和限制，请以你所在州的鱼类与野生动物管理机构为准。
          </li>
          <li>如果你未满 18 岁，请在父母或监护人的参与下使用 AI 回答。</li>
          <li>请向 AI 询问与钓鱼有关的问题。不得利用它制作有害、违法或冒犯性内容，规避其限制，或批量收集回答。</li>
          <li>
            为了撰写回答，你的问题以及与之匹配的指南段落会发送给我们的 AI 服务提供商
            Anthropic。不要在问题中填写个人信息，无论是你自己的还是他人的。详见<Link href="/privacy">隐私政策</Link>。
          </li>
          <li>
            免费账户每天可获得一定次数的 AI 回答，次数显示在按钮旁。FishEye Plus 在个人使用范围内不设每日上限；如果某个账户的使用看起来属于自动化或滥用行为，我们可能限制或暂停其
            AI 回答。
          </li>
          <li>
            AI 回答有时可能无法使用，例如我们的服务提供商出现故障，或 FishEye 暂停了该功能。我们可以随时更改、限制或停止 AI 回答。
          </li>
          <li>
            你可以将获得的回答用于自己的钓鱼活动。如需分享，请先核实，并注明来自 AI。其他人提出相同的问题，可能会得到相同或类似的回答。
          </li>
        </ul>
      </section>

      <section id="plus">
        <Heading id="plus" titles={TITLES} />
        <p>
          FishEye Plus 是一项会员服务。其具体内容以开通时的说明为准；目前，它取消了 AI 回答的每日次数限制。FishEye 也可能向部分账户免费提供
          Plus。
        </p>
        <ul>
          <li>
            <strong>付款前</strong>
            ，你会看到价格、扣费周期、自动续订的说明以及取消方式。完成购买即表示你授权该笔扣费以及此后每次续订的扣费，直到你取消。
          </li>
          <li>
            <strong>续订。</strong>Plus 会在每个周期结束时按当时的价格自动续订，直到你取消。年度会员续订前，我们会提醒你价格和取消方式。
          </li>
          <li>
            <strong>取消。</strong>你可以随时取消：如果是在应用内购买的 Plus，请在 Apple 或 Google
            账户设置中取消（删除应用不会取消订阅）；如果是在网站上购买的，请在<Link href="/account">账户页面</Link>
            取消。取消后不再续订；在已付费的周期结束前，你仍可使用 Plus。
          </li>
          <li>
            <strong>免费试用。</strong>如果你开始免费试用，试用结束时将自动转为付费会员，除非你在此之前取消。开始试用时，我们会告诉你具体日期。
          </li>
          <li>
            <strong>价格变动。</strong>我们可能调整 Plus 的价格。新价格对你适用之前，我们会通知你，并留出取消的时间。
          </li>
          <li>
            <strong>退款。</strong>除法律另有规定或我们另有说明外，已付款项不予退还，未用完的周期也不予退款。通过 Apple 或 Google
            购买的，只能按照其政策退款；请向其申请。
          </li>
          <li>
            <strong>如果我们停止提供 Plus</strong>，或在你没有违反本条款的情况下关闭你的账户，我们会退还已付费周期中未使用部分的费用。
          </li>
          <li>
            <strong>免费获得的 Plus</strong> 在说明的期限内有效，没有现金价值，也不能转让。
          </li>
          <li>价格可能不含税。适用的税费由你承担。</li>
        </ul>
      </section>

      <section id="your-content">
        <Heading id="your-content" titles={TITLES} />
        <p>
          你发布的渔获、照片、笔记和评论，所有权归你。为了让 FishEye 正常运作，你授予 FishEye
          一项全球范围、非独占、免版税的许可，允许其在 FishEye
          中存储、复制（例如生成照片的缩小版本或备份）和展示这些内容：公开的渔获或评论向所有人展示，私密的只向你（和管理员）展示。该许可在你删除相关内容或账户时终止；备份中的副本除外，这些副本会随时间被替换。
        </p>
        <ul>
          <li>
            你对自己发布的内容负责。只发布你拍摄的或有权使用的照片；未经他人同意，不要发布他人的照片，也不要发布任何人的个人信息。
          </li>
          <li>
            发布渔获时，你可以选择谁能看到它以及位置的精确程度。照片本身仍可能暴露地点，发布前请想清楚。不要发布会让人进入私人土地的钓点。
          </li>
          <li>
            内容发布前，我们不会逐一审核，也不为其他钓友发布的内容背书。他们的渔获和评论由他们负责，可能有误。我们也不核实其他钓友的身份：与只在
            FishEye 上认识的人见面前，请保持基本的警惕。
          </li>
          <li>如果你向我们提出想法或反馈，我们可以自由使用，无需向你付费，也不对你承担任何义务。</li>
        </ul>
      </section>

      <section id="rules">
        <Heading id="rules" titles={TITLES} />
        <p>不得利用 FishEye：</p>
        <ul>
          <li>违反法律，包括有关钓鱼、野生动物、划船和擅自闯入的法律，或展示自己、鼓励他人从事这类行为；</li>
          <li>骚扰、威胁、跟踪或冒充任何人，或发布他人的个人信息；</li>
          <li>
            使用侮辱性称呼，或因种族、民族、国籍、宗教、性别、性取向、性别认同、年龄或残疾而攻击他人（含有侮辱性称呼的名称和渔获不予接受）；
          </li>
          <li>
            发布垃圾信息、广告、色情内容、无端的暴力或血腥内容，或任何你无权发布的内容。任何将未成年人性化的内容都会被删除，并报告有关当局；
          </li>
          <li>标注误导他人的地点，或未经许可引导他人进入私人土地；</li>
          <li>使用机器人或爬虫从 FishEye 收集数据，批量复制其指南或数据，将其用于训练 AI 模型，或借此建立竞争性服务；</li>
          <li>另建账户、共享或出售账户，或规避 FishEye 的限制、封禁或安全措施；</li>
          <li>探测、破坏 FishEye 的系统或使其过载，上传恶意软件，或在法律允许的范围之外对 FishEye 进行反向工程；</li>
          <li>试图让 AI 生成有害内容或无视其指令。</li>
        </ul>
      </section>

      <section id="moderation">
        <Heading id="moderation" titles={TITLES} />
        <ul>
          <li>
            任何拥有账户的人都可以举报公开的渔获或评论。对于违反本条款的内容和账户，或在法律要求、为保护他人或 FishEye
            时，管理员可以隐藏或删除内容、限制功能，或暂停、关闭账户。除非法律或他人安全不允许，我们通常会说明原因。如果你认为我们处理有误，请写信给我们。
          </li>
          <li>
            你可以随时在<Link href="/account">账户页面</Link>删除账户。删除账户不会取消通过 Apple 或 Google 购买的
            Plus；请在相应平台取消。
          </li>
          <li>
            账户关闭后，第 {sec("your-content")} 条（在内容被删除前，你对所分享内容授予的许可）以及第 {sec("our-content")}{" "}
            条至第 {sec("general")} 条仍然有效。
          </li>
        </ul>
      </section>

      <section id="our-content">
        <Heading id="our-content" titles={TITLES} />
        <p>
          FishEye 的指南、文字、设计、代码、名称和标志，以及数据的编排方式，归 FishEye
          或向我们授权的人所有。我们授予你一项个人、非商业、不可转让的许可，允许你按照本条款使用
          FishEye；如果你违反本条款，该许可即告终止。欢迎自由分享链接，也可以在注明出处的前提下少量引用；但不得批量复制指南或数据、出售它们，或将其冒充为自己的作品。
        </p>
      </section>

      <section id="third-parties">
        <Heading id="third-parties" titles={TITLES} />
        <ul>
          <li>
            FishEye 使用来自政府机构和开放项目的公开数据，并在数据出现的位置和<Link href="/sources">来源</Link>
            页面注明出处。地图数据 © OpenStreetMap 贡献者；地图来自 MapTiler；鱼类照片来自 Wikimedia
            Commons，各有其许可。上述数据适用其各自的许可和条款。
          </li>
          <li>指向政府机构网站和其他网站的链接仅为方便你使用。我们无法控制这些网站，也不对其负责。</li>
          <li>
            你与 FishEye 一起使用的服务，例如“使用 Google 登录”、Apple 的 App Store、Google Play
            以及你的移动数据套餐，各有其条款。使用 FishEye 时，你必须遵守这些条款。
          </li>
        </ul>
      </section>

      <section id="copyright">
        <Heading id="copyright" titles={TITLES} />
        <p>
          如需举报侵犯你版权的内容，或回应针对你内容的举报，请参阅<Link href="/copyright">版权与内容</Link>
          页面。对于屡次侵权的用户，我们会关闭其账户。
        </p>
      </section>

      <section id="safety">
        <Heading id="safety" titles={TITLES} />
        <p>
          钓鱼、划船、涉水、冰钓以及前往水边都存在实际风险，包括溺水、冷水、失温、跌倒、雷击、高温、鱼钩和刀具、野生动物以及道路事故。FishEye
          看不到你所在地的实际情况。
        </p>
        <ul>
          <li>是否出行、去哪里、何时去、怎样去，完全由你决定；你对自身安全以及同行者（尤其是儿童）的安全负责。</li>
          <li>
            出发前查看天气和水情，并把行程告诉他人；乘船以及靠近深水或急流时穿好救生衣；不确定冰面是否安全时，不要上冰。
          </li>
          <li>FishEye 不是紧急救援服务。遇到紧急情况，请拨打 911。</li>
        </ul>
        <p className="legal-conspicuous">
          在法律允许的最大范围内，你承担你的钓鱼、划船、出行及其他活动的全部风险，包括无法预见的风险，以及因依赖 FishEye
          而产生的任何风险。
        </p>
      </section>

      <section id="disclaimers">
        <Heading id="disclaimers" titles={TITLES} />
        <p className="legal-conspicuous">
          FishEye 按“现状”和“现有可用状态”提供。在法律允许的最大范围内，FishEye 不对 FishEye
          或其中的任何内容（包括其信息、地图、预报、AI
          回答、拍照识别和他人发布的内容）作出任何明示或默示的承诺或保证。这包括对其准确、完整、及时、可靠、安全、可用、不中断或无错误的任何承诺，以及对适销性、特定用途适用性、所有权和不侵权的默示保证。
        </p>
        <p>有些地方不允许排除其中部分保证。在这些地方，上述排除在法律允许的范围内适用。</p>
      </section>

      <section id="liability">
        <Heading id="liability" titles={TITLES} />
        <p>在本条款中，“FishEye 相关方”是指 FishEye、其运营者，以及参与 FishEye 工作或为其工作的人员。</p>
        <div className="legal-conspicuous">
          <p>在法律允许的最大范围内：</p>
          <ul>
            <li>
              FishEye
              相关方不对间接、附带、特殊、后果性、惩戒性或惩罚性损害赔偿，或利润、数据或商誉的损失承担责任，即使已被告知可能发生此类损害；
            </li>
            <li>
              对于你在钓鱼、划船或出行时发生的任何事情，在你通过 FishEye 找到的地点发生的任何事情，罚款或处罚，以及你根据 FishEye 的信息或 AI
              回答作出的决定，FishEye 相关方均不承担责任；
            </li>
            <li>
              就所有与 FishEye 或本条款有关的索赔，FishEye 相关方的总责任以 {LEGAL.liabilityFloorUsd} 美元与索赔发生前 12
              个月内你向 FishEye 支付的金额两者中的较高者为限。
            </li>
          </ul>
          <p>无论依据何种法律理论（合同、保证、过失、严格责任或其他），上述限制均适用。</p>
        </div>
        <p>
          上述限制不限制因重大过失、故意不当行为或欺诈而产生的责任，也不限制法律不允许限制的任何责任。有些地方不允许这些限制，因此其中部分可能不适用于你。
        </p>
      </section>

      <section id="release">
        <Heading id="release" titles={TITLES} />
        <p className="legal-conspicuous">
          在法律允许的最大范围内，对于因你的钓鱼、划船、出行或其他活动，因依赖 FishEye 上的信息、地图、预报或 AI
          回答，或因你与其他钓友或任何其他人（例如土地所有者）之间的争议而造成的人身伤害、死亡、财产损失或其他损失，你免除
          FishEye 相关方的一切已知或未知的索赔责任，包括基于 FishEye
          相关方过失的索赔，并承诺不就此类索赔起诉他们。本免责不涵盖重大过失或故意不当行为。
        </p>
        <p>
          如果你居住在加利福尼亚州，你放弃《加利福尼亚州民法典》第 1542
          条赋予的权利。该条规定：“概括性免责不适用于债权人或免责方在签署免责书时不知道或未怀疑存在的、对其有利的索赔；若其知道这些索赔，将会对其与债务人或被免责方的和解产生重大影响。”你同样放弃其他地方任何类似法律赋予的权利。
        </p>
      </section>

      <section id="indemnity">
        <Heading id="indemnity" titles={TITLES} />
        <p>
          在法律允许的范围内，对于他人因你发布的内容、你违反本条款或法律，或你的钓鱼或其他活动（例如在你标注的钓点擅自闯入）而提出的索赔，以及由此产生的损失、费用和合理的律师费，你将为
          FishEye 相关方进行抗辩并予以赔偿。我们会将此类索赔告知你，可以选择自行负责抗辩，你应在合理需要的范围内提供协助。
        </p>
      </section>

      <section id="disputes">
        <Heading id="disputes" titles={TITLES} />
        <p className="legal-conspicuous">请仔细阅读本条。它影响你的权利，包括向法院起诉的权利。</p>
        <p>
          <strong>先与我们沟通。</strong>大多数问题都可以通过沟通解决。在启动仲裁或诉讼之前，请发送通知至{" "}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
          ，邮件主题为“Dispute”（争议），写明你的姓名、账户邮箱、事情经过以及你的诉求。我们会将我们的通知发送到你的账户邮箱。随后双方在
          60 天内本着诚意尝试解决；在此期间，该索赔的任何时效均暂停计算。
        </p>
        <p>
          <strong>仲裁。</strong>如果争议未能解决，你与 FishEye 同意，因本条款或 FishEye
          引起或与之相关的任何争议或索赔（“索赔”），均由一名仲裁员以个人名义进行具有约束力的仲裁裁决，而不通过法院解决，但以下情况除外：
        </p>
        <ul>
          <li>任何一方均可在符合条件时，向小额诉讼法院提起个人索赔；</li>
          <li>任何一方均可请求法院制止对其知识产权的侵犯或滥用；</li>
          <li>如果你按下文所述选择退出，本段不适用。</li>
        </ul>
        <p>
          本条受《联邦仲裁法》管辖。仲裁由美国仲裁协会（AAA）依照其《消费者仲裁规则》进行，适用时依照其大规模仲裁规则（见
          adr.org）。仲裁员可以裁决给予你与法院相同的个人救济。对于你提起的索赔，FishEye 承担 AAA
          的立案费、管理费和仲裁员费用中超出你向法院起诉所需费用的部分，除非仲裁员认定你的索赔属于无理索赔。任何听证均以视频或电话方式进行；如果你愿意，也可以在你居住的县当面进行。
        </p>
        <p className="legal-conspicuous">
          不适用集体诉讼。你与 FishEye
          只能以个人名义相互提出索赔，不得作为任何集体、群体、合并或代表诉讼程序的原告或成员。如果本句对某项索赔被认定为不可执行，该索赔应提交法院而非仲裁。如果法律不允许将公共禁令救济的请求提交仲裁，该请求在个人仲裁结束后提交法院。如果索赔提交法院，在法律允许的范围内，你与
          FishEye 均放弃陪审团审理。
        </p>
        <p>
          <strong>选择退出。</strong>你可以在首次接受本条款后的 {optOut} 天内选择退出仲裁：发送邮件至{" "}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
          ，邮件主题为“Arbitration opt-out”（退出仲裁），并写明你的姓名和账户邮箱。选择退出不会改变本条款的其他任何内容。
        </p>
        <p>
          <strong>本条的变更。</strong>本条的变更不适用于任何一方已发出通知的索赔。如果我们作出重要变更，你可以在 30
          天内发邮件拒绝该变更，此前的版本将继续对你适用。
        </p>
        <p>
          <strong>时效。</strong>在法律允许的范围内，索赔必须在其发生后两年内提起，否则不得再提起。
        </p>
        <p>
          <strong>适用法律和法院。</strong>本条款受{STATE}法律管辖，不考虑法律冲突规则；本条同时受《联邦仲裁法》管辖。未经仲裁的索赔应提交位于
          {STATE}的州法院或联邦法院，你与 FishEye 同意接受其管辖，除非你居住地的法律赋予你在当地提起诉讼的权利。
        </p>
      </section>

      <section id="changes">
        <Heading id="changes" titles={TITLES} />
        <ul>
          <li>
            我们可能更改 FishEye、增加或移除功能，或停止提供 FishEye。如果我们停止提供你已付费的服务，第 {sec("plus")}{" "}
            条说明了你可以获得的退款。
          </li>
          <li>
            我们可能修改本条款。我们会更新页首的日期；对于重要变更，我们会在变更生效至少 {LEGAL.noticeDays}{" "}
            天前通过网站或电子邮件通知你，除非法律要求更早变更，或变更涉及新功能。变更生效后你继续使用
            FishEye，即表示接受变更。如果你不接受，请停止使用 FishEye 并删除账户。
          </li>
          <li>标注为新功能或测试功能的部分，出错的可能性高于其他部分，并且可能会变更或下线。</li>
        </ul>
      </section>

      <section id="app-stores">
        <Heading id="app-stores" titles={TITLES} />
        <p>如果你是从 Apple 的 App Store 获取的 FishEye 应用：</p>
        <ul>
          <li>本条款仅存在于你与 FishEye 之间，而非你与 Apple 之间。对应用及其内容负责的是 FishEye，而不是 Apple。</li>
          <li>
            你对应用的许可不可转让，并且仅限于在你拥有或控制的 Apple 品牌产品上使用，具体以
            Apple《媒体服务条款与条件》中的《使用规则》（包括“家人共享”）允许的范围为准。本条款与该《使用规则》冲突时，就该应用而言，以《使用规则》为准。
          </li>
          <li>应用的维护和支持由 FishEye 而非 Apple 提供。Apple 没有提供维护和支持的义务。</li>
          <li>
            如果应用不符合任何适用的保证，你可以通知 Apple，Apple 将退还该应用的购买价款（如有）。在法律允许的范围内，Apple
            对该应用不承担其他任何保证义务；因此类不符合而产生的任何其他索赔、损失或费用，在本条款未予排除的范围内，由 FishEye 负责。
          </li>
          <li>
            与应用或你使用应用有关的任何索赔，包括产品责任索赔、关于应用不符合法律或监管要求的索赔，以及依据消费者保护、隐私或类似法律提出的索赔，均由
            FishEye 而非 Apple 负责。
          </li>
          <li>
            如果有人声称应用或你对应用的使用侵犯了其知识产权，由 FishEye 而非 Apple 负责调查、抗辩、和解和了结该索赔。
          </li>
          <li>Apple 及其子公司是本条款的第三方受益人。你接受本条款后，Apple 有权对你执行本条款。</li>
        </ul>
        <p>如果你是从 Google Play 获取的应用，你的购买受 Google 的条款约束，Google 不对该应用负责。</p>
      </section>

      <section id="general">
        <Heading id="general" titles={TITLES} />
        <ul>
          <li>本条款、隐私政策、版权页面以及针对特定功能显示的任何条款，构成你与 FishEye 之间关于 FishEye 的完整协议。</li>
          <li>
            如果本条款的某一部分无法执行，该部分将在使其可执行所需的最小范围内予以修改，其余部分仍然有效。我们未执行某一部分，并不代表我们放弃该部分。
          </li>
          <li>你不得转让本条款或你的账户。我们可以转让，例如转让给接手运营 FishEye 的公司，或在合并、出售时转让。</li>
          <li>对于因超出我们合理控制范围的事件造成的延误或未能履行，我们不承担责任。</li>
          <li>
            本条款并不使你与 FishEye 成为合伙人、雇主与雇员或彼此的代理人。除 FishEye 相关方（第 {sec("liability")}{" "}
            条至第 {sec("indemnity")} 条）和 Apple（第 {sec("app-stores")} 条）外，任何其他人均无权执行本条款。
          </li>
          <li>
            我们可以通过发送到你账户邮箱的电子邮件或在 FishEye
            上向你发送通知；你同意电子形式的通知和协议与书面形式具有同等效力。你可以按下方联系方式向我们发送通知。
          </li>
          <li>本条款以英文撰写。任何译文仅为方便阅读而提供，以英文版本为准。“包括”指“包括但不限于”。</li>
          <li>
            加利福尼亚州居民：可以书面形式联系加利福尼亚州消费者事务部消费者服务处投诉协助组，地址为 1625 North Market Blvd., Suite N
            112, Sacramento, CA 95834，或致电 (800) 952-5210。
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
        <p>有关 FishEye 或应用的问题、投诉和索赔，请发送至此邮箱。</p>
      </section>
    </>
  );
}

export const zh: TermsText = {
  title: "使用条款",
  lede: "这是你与 FishEye 之间的协议。请仔细阅读：它要求你为自身安全负责，限制了 FishEye 承担的责任，并规定大多数争议通过个人仲裁解决。",
  description: "使用 FishEye 的协议：钓鱼信息、AI 回答、FishEye Plus、你分享的内容以及争议解决。",
  Body,
};
