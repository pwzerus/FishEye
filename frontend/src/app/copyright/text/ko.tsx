import Link from "next/link";

import { LEGAL, type LegalText } from "@/lib/legal";

import { NOTICE_SUBJECT, noticeHref } from "./en";

// Korean translation of en.tsx, section for section. The English version
// is the one that applies. Change this with en.tsx.
// Each paragraph stays on one line: JSX turns a line break into a space.

function Body() {
  return (
    <>
      <section>
        <h2>규칙을 어기는 조과</h2>
        <p>
          조과를 열고 <strong>신고</strong>를 누르십시오. 이유(스팸, 부적절한 사진, 잘못된 위치, 사유지, 위험하거나 불법적인 내용)를 고르고 메모를 덧붙이십시오. 여러 사람이 신고한 조과는 관리자가 확인할 때까지 숨겨집니다. 신고하려면 계정이 필요하므로, 한 사람이 혼자서 조과를 숨길 수는 없습니다.
        </p>
        <p>
          다른 사람이 이용자의 개인정보를 게시했거나, 어떤 조과가 사람들을 이용자의 땅으로 안내하는 등 그 밖의 경우에는 링크를 첨부하여 이메일(<a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>)로 보내 주십시오.
        </p>
      </section>

      <section>
        <h2>저작권 침해 통지</h2>
        <p>
          FishEye에 있는 무언가가 이용자의 저작물을 허락 없이 사용하고 있다면, 제목을 “{NOTICE_SUBJECT}”(저작권 통지)로 하고 다음 내용을 담은 통지를 이메일(<a href={noticeHref}>{LEGAL.contactEmail}</a>)로 보내 주십시오.
        </p>
        <ol>
          <li>침해되었다고 주장하는 저작물</li>
          <li>그 저작물을 사용하는 FishEye의 조과나 페이지 링크</li>
          <li>이름, 우편 주소, 전화번호, 이메일 주소</li>
          <li>해당 사용이 이용자, 대리인 또는 법률에 의해 허락되지 않았다고 선의로 믿는다는 진술</li>
          <li>통지의 정보가 정확하며, 위증 시 처벌을 감수하고, 이용자가 저작권자이거나 저작권자를 대신하여 행동할 권한이 있다는 진술</li>
          <li>자필 서명 또는 전자 서명(전체 이름을 입력하면 됩니다)</li>
        </ol>
        <p>
          당사는 해당 콘텐츠를 내리고, 게시한 사람에게 알리며, 통지 사본을 전달합니다. 알면서 허위로 주장한 사람은 손해배상 책임을 질 수 있습니다.
        </p>
      </section>

      <section>
        <h2>조과가 삭제된 경우</h2>
        <p>
          실수로 삭제되었다고 생각하거나 게시할 권리가 있다면, 같은 주소로 반론 통지를 보내십시오. 통지에는 삭제된 내용의 링크, 실수나 오인으로 삭제되었다고 선의로 믿는다는 위증 시 처벌을 감수한 진술, 이름, 주소, 전화번호, 이용자 주소지를 관할하는 연방 법원(미국 밖이라면 FishEye가 있을 수 있는 모든 법원)의 관할과 통지를 보낸 사람의 송달을 받는 데 대한 동의, 그리고 서명이 들어가야 합니다. 신고한 사람이 영업일 기준 10일 이내에 소송을 제기했다고 알리지 않으면, 당사는 해당 콘텐츠를 복원할 수 있습니다.
        </p>
      </section>

      <section>
        <h2>반복 침해자</h2>
        <p>
          다른 사람의 저작권을 침해하는 콘텐츠를 반복해서 게시하는 사람의 계정은 해지합니다. <Link href="/terms">이용약관</Link>도 참고하십시오.
        </p>
      </section>
    </>
  );
}

export const ko: LegalText = {
  title: "저작권 및 콘텐츠",
  lede: "규칙을 어기는 조과나, 권리자의 허락 없이 게시된 사진이나 글을 당사에 알리는 방법입니다.",
  description: "규칙을 어기는 조과나 이용자의 저작권을 침해하는 콘텐츠를 신고하는 방법입니다.",
  Body,
};
