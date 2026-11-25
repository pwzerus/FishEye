import { describe, expect, it } from "vitest";

import type { Locale } from "@/i18n/config";
import { findSeeRefs, type TopicTitle } from "./seeRefs";

const EN: TopicTitle[] = [
  { id: "technique-drag", title: "Setting the drag" },
  { id: "cond-cover", title: "Cover: weeds, wood and docks" },
  { id: "cond-points", title: "Points, drop-offs and inlets" },
  { id: "technique-bite", title: "Is it a bite? Setting the hook" },
  { id: "tackle-split-shot", title: "Split shot" },
  { id: "tackle-bobbers", title: "Bobbers (floats)" },
  { id: "rig-bottom", title: "Sliding sinker bottom rig" },
  { id: "trouble-line-twist", title: "Line twist, loops and tangles on a spinning reel" },
];

const linked = (text: string, locale: Locale, titles: TopicTitle[]) =>
  findSeeRefs(text, locale, titles).map((r) => [text.slice(r.start, r.end), r.topic]);

describe("findSeeRefs", () => {
  it("finds a reference by a topic's title or its first part", () => {
    expect(linked("Resist tightening the drag (see Setting the drag).", "en", EN)).toEqual([["Setting the drag", "technique-drag"]]);
    expect(linked("Set it soon (see Is it a bite?).", "en", EN)).toEqual([["Is it a bite?", "technique-bite"]]);
    expect(linked("(see Line twist)", "en", EN)).toEqual([["Line twist", "trouble-line-twist"]]);
  });

  it("splits a list of names, even where a title has a comma or an 'and' in it", () => {
    expect(linked("(see Cover and Points, drop-offs and inlets)", "en", EN)).toEqual([
      ["Cover", "cond-cover"],
      ["Points, drop-offs and inlets", "cond-points"],
    ]);
    expect(linked("(see Split shot, Bobbers and Sliding sinker bottom rig)", "en", EN)).toEqual([
      ["Split shot", "tackle-split-shot"],
      ["Bobbers", "tackle-bobbers"],
      ["Sliding sinker bottom rig", "rig-bottom"],
    ]);
  });

  it("reads each language's way of writing it", () => {
    const drag = (title: string): TopicTitle[] => [{ id: "technique-drag", title }];
    expect(linked("搏鱼中途不要拧紧卸力（见“调卸力”）。", "zh", drag("调卸力"))).toEqual([["调卸力", "technique-drag"]]);
    expect(linked("搏魚中途不要擰緊卸力（見「調卸力」）。", "zht", drag("調卸力"))).toEqual([["調卸力", "technique-drag"]]);
    expect(linked("我慢してください（「ドラグの調整」を参照）。", "ja", drag("ドラグの調整"))).toEqual([["ドラグの調整", "technique-drag"]]);
    expect(linked("a media pelea (consulta Ajustar el freno).", "es", drag("Ajustar el freno"))).toEqual([["Ajustar el freno", "technique-drag"]]);
    expect(linked("참으세요(드랙 조절하기 참고).", "ko", drag("드랙 조절하기"))).toEqual([["드랙 조절하기", "technique-drag"]]);
  });

  it("finds Korean names in single quotes, a quoted name a title begins with, and a name after words of its own", () => {
    const release: TopicTitle[] = [{ id: "care-release", title: "캐치 앤 릴리스: 놓아줄 물고기 다루기" }];
    expect(linked("놓아주세요('캐치 앤 릴리스' 참고).", "ko", release)).toEqual([["캐치 앤 릴리스", "care-release"]]);
    const line: TopicTitle[] = [
      { id: "rule-line-disposal", title: "旧鱼线怎么处理" },
      { id: "trouble-line-twist", title: "纺车轮的线打卷、打圈和缠线" },
    ];
    expect(linked("（见“纺车轮的线打卷”和“旧鱼线”）", "zh", line)).toEqual([
      ["纺车轮的线打卷", "trouble-line-twist"],
      ["旧鱼线", "rule-line-disposal"],
    ]);
    const omori: TopicTitle[] = [{ id: "tackle-sinkers", title: "オモリ：エッグ、バレット、コーン、ピラミッド" }];
    expect(linked("釣具店で買えます（タングステンもその一つです。「オモリ」を参照）。", "ja", omori)).toEqual([["オモリ", "tackle-sinkers"]]);
    const sinkers: TopicTitle[] = [{ id: "tackle-sinkers", title: "봉돌: 에그, 불릿, 콘, 피라미드" }];
    expect(linked("(납 대신 쓰는 금속도 있어요. 텅스텐이 그중 하나예요. 봉돌 참고)", "ko", sinkers)).toEqual([["봉돌", "tackle-sinkers"]]);
  });

  it("leaves a name that is no topic's, and other brackets, as text", () => {
    expect(linked("(see Texas bait rules)", "en", EN)).toEqual([]);
    expect(linked("Bobbers (floats) hold bait up.", "en", EN)).toEqual([]);
  });

  it("picks the topic for every state over one state's card of the same title", () => {
    const titles: TopicTitle[] = [
      { id: "care-release-tx", title: "Catch and release", region: "TX" },
      { id: "care-release", title: "Catch and release: handling a fish you'll let go", region: "all" },
    ];
    expect(linked("(see Catch and release)", "en", titles)).toEqual([["Catch and release", "care-release"]]);
  });
});
