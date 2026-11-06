/**
 * 증시 전망 페이지(src/market/*.md)의 고정 구성과 게시 금지 표현을 검사합니다.
 * pnpm test는 배포 워크플로의 빌드 앞 단계이므로, 여기서 실패하면 배포가 중단됩니다.
 * 표현 검사는 명백한 문구만 거르는 장치일 뿐이며, 게시 전 법률 검토를 대신하지 않습니다.
 *
 * 실행 방법: pnpm test
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { describe, it } from "node:test";

const MARKET_DIR = new URL("../src/market/", import.meta.url);

const SECTIONS = ["## ① ", "## ② ", "## ③ ", "**[투자 주의사항 및 면책 조항]**"];
const CARDS = ["필라델피아 반도체", "나스닥종합", "S&P500", "WTI"];
const COLUMNS = ["미국 섹터", "미국 테마", "한국 테마", "근거"];
const DISCLAIMER =
  "본 게시물은 미국 및 한국 증시 테마에 대한 단순 정보 제공을 목적으로 작성되었습니다. 특정 종목의 매수 또는 매도를 추천하는 것이 아니며, 모든 투자 판단의 책임과 결과는 투자자 본인에게 귀속됩니다. 과거의 수익률이 미래의 수익을 보장하지 않으므로 신중하게 투자하시기 바랍니다.";

// 매매 권유, 수익 보장, 근거 없는 단정으로 읽히는 표현입니다. 면책 조항 본문은 검사에서 뺍니다.
const FORBIDDEN = [
  /(종목|매수|매도)\s*(을|를)?\s*(추천|권유)/u,
  /추천\s*(종목|주식)/u,
  /목표\s*(주가|가)/u,
  /(수익|원금)\s*(을|를)?\s*(보장|확정)/u,
  /(수익률|수익)\s*\d/u,
  /(무조건|반드시|확실히|틀림없이)\s*(오른다|오를|상승|급등|수익)/u,
  /(급등|상한가)\s*(예정|임박|확정)/u,
  /(지금|당장)\s*(사세요|사야|매수|매도|파세요|팔아)/u,
  /(리딩방|VIP\s*회원|유료\s*회원|비공개\s*정보|내부\s*정보|작전주)/u,
];

const matchAll = (text: string, pattern: RegExp) => [...text.matchAll(pattern)].map((match) => match[1].trim());

const pages = readdirSync(MARKET_DIR).filter((name) => /^\d{4}-\d{2}-\d{2}\.md$/u.test(name));

describe("증시 전망 페이지", () => {
  it("날짜별 페이지가 하나 이상 있음", () => {
    assert.ok(pages.length > 0, "src/market/에 날짜별 페이지가 없습니다");
  });

  for (const name of pages) {
    const text = readFileSync(new URL(name, MARKET_DIR), "utf8");

    it(`${name}: 구획 순서가 고정되어 있음`, () => {
      const positions = SECTIONS.map((section) => text.indexOf(section));
      assert.ok(!positions.includes(-1), `빠진 구획이 있습니다: ${positions.join(", ")}`);
      assert.deepEqual(positions, [...positions].sort((a, b) => a - b), "구획 순서가 다릅니다");
    });

    it(`${name}: 요약 카드 4개가 정해진 순서임`, () => {
      assert.deepEqual(matchAll(text, /market-card__name">([^<]+)</gu), CARDS);
    });

    it(`${name}: 표의 열과 상승·하락 구획이 맞고 구획당 10개 이하임`, () => {
      assert.deepEqual(matchAll(text, /<th scope="col">([^<]+)</gu), COLUMNS);
      const blocks = matchAll(text, /<tbody class="market-themes__(?:up|down)">([\s\S]*?)<\/tbody>/gu);
      assert.equal(blocks.length, 2, "상승·하락 구획이 각각 하나씩 있어야 합니다");
      for (const block of blocks) {
        const rows = block.match(/<tr>/gu)?.length ?? 0;
        assert.ok(rows >= 1 && rows <= 10, `구획의 행 수가 범위를 벗어났습니다: ${rows}`);
      }
    });

    it(`${name}: 면책 조항이 원문 그대로 맨 끝에 있음`, () => {
      assert.ok(text.trimEnd().endsWith(DISCLAIMER), "면책 조항이 맨 끝에 원문 그대로 있어야 합니다");
    });

    it(`${name}: 게시 금지 표현이 없음`, () => {
      const body = text.replace(DISCLAIMER, "");
      for (const pattern of FORBIDDEN) {
        assert.equal(body.match(pattern)?.[0], undefined, `게시 금지 표현을 찾았습니다: ${pattern}`);
      }
    });
  }
});
