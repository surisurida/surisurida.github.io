/**
 * 증시 전망 페이지의 고정 구성과 게시 금지 표현을 검사합니다.
 * 배포 때 만드는 src/news/market/*.md와, 저장소에 있는 형식 본보기(scripts/market_brief/)가 대상입니다.
 * pnpm test는 증시 전망 작성 뒤에도 빌드 앞에서 다시 돌기 때문에, 여기서 실패하면 배포가 중단됩니다.
 * 표현 검사는 명백한 문구만 거르는 장치일 뿐이며, 게시 전 법률 검토를 대신하지 않습니다.
 *
 * 실행 방법: pnpm test
 */
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { describe, it } from "node:test";

import { marketSummary } from "../src/.vuepress/market.ts";

const PAGE_DIRS = [new URL("../src/news/market/", import.meta.url), new URL("../scripts/market_brief/", import.meta.url)];

const SECTIONS = ["## ① ", "## ② ", "## ③ ", "**[투자 주의사항 및 면책 조항]**"];
const CARDS = ["필라델피아 반도체", "나스닥종합", "S&P500", "WTI"];
const COLUMNS = ["미국 섹터", "미국 테마", "한국 테마", "근거"];
const DISCLAIMER =
  "본 게시물은 미국 및 한국 증시 테마에 대한 단순 정보 제공을 목적으로 작성되었습니다. 특정 종목의 매수 또는 매도를 추천하는 것이 아니며, 모든 투자 판단의 책임과 결과는 투자자 본인에게 귀속됩니다. 과거의 수익률이 미래의 수익을 보장하지 않으므로 신중하게 투자하시기 바랍니다.";
const AI_NOTICE = "이 페이지는 AI가 공개 자료를 조사해 작성했으며";
const WEEKDAYS = "일월화수목금토";
const DAY_MS = 86_400_000;

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

// 사람이 보지 않고 게시될 수 있으므로, 표에 필요한 태그 말고는 페이지에 넣지 못하게 합니다.
const ALLOWED_TAGS = new Set(["a", "br", "div", "p", "table", "tbody", "td", "th", "thead", "tr"]);

const matchAll = (text: string, pattern: RegExp) => [...text.matchAll(pattern)].map((match) => match[1].trim());

const pages = PAGE_DIRS.flatMap((dir) =>
  existsSync(dir)
    ? readdirSync(dir)
        .filter((name) => /^\d{4}-\d{2}-\d{2}\.md$/u.test(name))
        .map((name) => ({ name, url: new URL(name, dir) }))
    : [],
);

describe("증시 전망 페이지", () => {
  it("형식 본보기 페이지가 있음", () => {
    assert.ok(pages.length > 0, "scripts/market_brief/에 날짜 이름의 본보기 페이지가 없습니다");
  });

  for (const { name, url } of pages) {
    const date = name.replace(/\.md$/u, "");
    const text = readFileSync(url, "utf8");

    it(`${name}: frontmatter가 파일 날짜와 맞음`, () => {
      assert.match(text, new RegExp(`^title: "${date} 증시 전망"$`, "mu"));
      assert.match(text, new RegExp(`^date: ${date}$`, "mu"));
      assert.match(text, /^containerClass: market-page$/mu);
      assert.doesNotMatch(text, /^redirectFrom:/mu, "/news/market/ 이동은 빌드 때 최신 페이지로 정해집니다");
    });

    it(`${name}: 구획 순서가 고정되어 있음`, () => {
      const positions = SECTIONS.map((section) => text.indexOf(section));
      assert.ok(!positions.includes(-1), `빠진 구획이 있습니다: ${positions.join(", ")}`);
      assert.deepEqual(positions, [...positions].sort((a, b) => a - b), "구획 순서가 다릅니다");
    });

    it(`${name}: 요약 카드 4개가 정해진 순서임`, () => {
      assert.deepEqual(matchAll(text, /market-card__name">([^<]+)</gu), CARDS);
    });

    it(`${name}: 카드의 방향과 등락률이 종가·변동폭과 맞음`, () => {
      const cards = [
        ...text.matchAll(
          /market-card--(up|down)">\s*<div class="market-card__name">([^<]+)<\/div>\s*<div class="market-card__value">\$?([\d,.]+)<\/div>\s*<div class="market-card__change">([▲▼]) ([\d,.]+) \(([-+][\d.]+)%\)<\/div>/gu,
        ),
      ];
      assert.equal(cards.length, CARDS.length, "카드 형식을 읽지 못했습니다");

      for (const [, direction, card, value, arrow, change, percent] of cards) {
        const sign = direction === "up" ? 1 : -1;
        const close = Number(value.replaceAll(",", ""));
        const delta = sign * Number(change.replaceAll(",", ""));
        assert.equal(arrow, direction === "up" ? "▲" : "▼", `${card}: 화살표와 방향이 다릅니다`);
        assert.ok(sign * Number(percent) >= 0, `${card}: 등락률 부호와 방향이 다릅니다`);
        // 종가와 변동폭도 반올림된 값이므로 표시 단위보다 조금 넓게 허용합니다.
        const computed = (delta / (close - delta)) * 100;
        assert.ok(
          Math.abs(computed - Number(percent)) <= 0.015,
          `${card}: 등락률 ${percent}%와 계산값 ${computed.toFixed(3)}%가 다릅니다`,
        );
      }
    });

    it(`${name}: 미국 기준일이 페이지 날짜 직전이고 요일이 맞음`, () => {
      const match = /(\d{1,2})\/(\d{1,2})\(([일월화수목금토])\) 뉴욕 정규장 종가 기준/u.exec(text);
      assert.ok(match, "① 구획에 'M/D(요일) 뉴욕 정규장 종가 기준' 문장이 없습니다");
      const [, month, day, weekday] = match;

      const page = Date.parse(`${date}T00:00:00Z`);
      const year = Number(date.slice(0, 4));
      const inYear = Date.UTC(year, Number(month) - 1, Number(day));
      // 1월 초 페이지의 기준일이 12월이면 전년도입니다.
      const close = inYear > page ? Date.UTC(year - 1, Number(month) - 1, Number(day)) : inYear;

      const days = (page - close) / DAY_MS;
      assert.ok(days >= 1 && days <= 5, `미국 기준일이 페이지 날짜보다 ${days}일 앞섭니다`);
      assert.equal(WEEKDAYS[new Date(close).getUTCDay()], weekday, "미국 기준일의 요일이 틀립니다");
    });

    it(`${name}: 메인 페이지 요약을 만들 수 있음`, () => {
      const summary = marketSummary(date, text);
      assert.equal(summary.link, `/news/market/${date}.html`);
      assert.deepEqual(
        summary.changes.split(" · ").map((item) => item.replace(/ [-+][\d.]+%$/u, "")),
        CARDS,
      );
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

    it(`${name}: AI 작성 안내가 있음`, () => {
      assert.ok(text.includes(AI_NOTICE), "AI 작성 안내 문장이 없습니다");
    });

    it(`${name}: 게시 금지 표현이 없음`, () => {
      const body = text.replace(DISCLAIMER, "");
      for (const pattern of FORBIDDEN) {
        assert.equal(body.match(pattern)?.[0], undefined, `게시 금지 표현을 찾았습니다: ${pattern}`);
      }
    });

    it(`${name}: 허용한 태그와 https 링크만 있음`, () => {
      const tags = matchAll(text, /<\/?([a-zA-Z][\w-]*)/gu).map((tag) => tag.toLowerCase());
      assert.deepEqual(
        tags.filter((tag) => !ALLOWED_TAGS.has(tag)),
        [],
        "허용하지 않은 태그가 있습니다",
      );
      assert.doesNotMatch(text, /\son\w+\s*=|\sstyle\s*=|\{\{|javascript:/iu, "실행될 수 있는 내용이 있습니다");

      const links = [...matchAll(text, /href="([^"]*)"/gu), ...matchAll(text, /\]\(([^)]*)\)/gu)];
      assert.deepEqual(
        links.filter((link) => !link.startsWith("https://")),
        [],
        "https가 아닌 링크가 있습니다",
      );
    });
  }
});
