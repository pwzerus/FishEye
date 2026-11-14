import Link from "next/link";

import { LEGAL, type LegalText } from "@/lib/legal";

import { NOTICE_SUBJECT, noticeHref } from "./en";

// 版权页的简体中文译文，逐节对应 en.tsx；以英文版为准。
// 改 en.tsx 时同步改这里，然后在 frontend/ 下运行 scripts/zh_hant.py 生成繁体版。
// 每段写在一行里：JSX 会把换行变成空格。

function Body() {
  return (
    <>
      <section>
        <h2>违反规则的渔获</h2>
        <p>
          打开该渔获，点击<strong>举报</strong>。选择原因（垃圾信息、不当照片、位置错误、私人财产、不安全或违法的内容），并添加说明。被多人举报的渔获会被隐藏，直到管理员查看。举报需要账户，因此任何人都无法独自隐藏一条渔获。
        </p>
        <p>
          其他情况，例如他人发布了你的个人信息，或某条渔获引导他人进入你的土地：请将链接发送至 <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>。
        </p>
      </section>

      <section>
        <h2>版权通知</h2>
        <p>
          如果 FishEye 上的内容未经许可使用了你享有版权的作品，请发送通知至 <a href={noticeHref}>{LEGAL.contactEmail}</a>，邮件主题为“{NOTICE_SUBJECT}”（版权通知），并提供：
        </p>
        <ol>
          <li>你认为被侵权的作品；</li>
          <li>FishEye 上使用该作品的渔获或页面的链接；</li>
          <li>你的姓名、邮寄地址、电话号码和电子邮箱地址；</li>
          <li>一份声明，表明你善意地相信该使用未经你、你的代理人或法律授权；</li>
          <li>一份声明，表明你通知中的信息准确无误，并在伪证罪处罚的前提下声明你是版权所有人或有权代表版权所有人行事；</li>
          <li>你的亲笔签名或电子签名（输入你的全名即可）。</li>
        </ol>
        <p>我们会删除相关内容，通知发布者，并向其提供通知的副本。明知虚假而提出主张的人，可能需要承担损害赔偿责任。</p>
      </section>

      <section>
        <h2>如果你的渔获被删除</h2>
        <p>
          如果你认为内容是被误删的，或你有权发布该内容，请向同一地址发送反通知，内容包括：被删除内容的链接；一份在伪证罪处罚的前提下作出的声明，表明你善意地相信该内容是因错误或误认而被删除；你的姓名、地址和电话号码；你同意接受你所在地址对应的联邦法院（如在美国境外，则为 FishEye 所在的任何法院）的管辖，并同意接受发出通知者的文书送达；以及你的签名。除非投诉人在 10 个工作日内告知我们其已向法院起诉，否则我们可能会恢复该内容。
        </p>
      </section>

      <section>
        <h2>屡次侵权者</h2>
        <p>
          对于屡次发布侵犯他人版权内容的用户，我们会关闭其账户。另请参阅<Link href="/terms">使用条款</Link>。
        </p>
      </section>
    </>
  );
}

export const zh: LegalText = {
  title: "版权与内容",
  lede: "如何告诉我们某条渔获违反了规则，或某张照片、某段文字未经权利人许可被发布。",
  description: "如何举报违反规则的渔获，或侵犯你版权的内容。",
  Body,
};
