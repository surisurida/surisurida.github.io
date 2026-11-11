import { existsSync, readdirSync, readFileSync } from "node:fs";

const MARKET_DIR = new URL("../news/market/", import.meta.url);
const WEEKDAYS = "일월화수목금토";

// 페이지의 카드 이름은 HTML 문맥이라 S&amp;P500처럼 엔티티로 쓰일 수 있습니다.
const decodeHtml = (text: string) =>
  text.replace(/&amp;/gu, "&").replace(/&#38;/gu, "&").replace(/&quot;/gu, '"').replace(/&#39;/gu, "'");

/**
 * 증시 전망(src/news/market/)의 날짜별 페이지 이름(YYYY-MM-DD)을 최신순으로 돌려줍니다.
 * 페이지는 scripts/write_market_brief.py가 로컬 스케줄러에서 만드는 일회성 파일이라, 아직 없으면 빈 목록입니다.
 * 메뉴·메인 요약·/news/market/ 이동은 빌드 시점의 이 목록을 씁니다.
 */
export const marketDates = (): string[] =>
  existsSync(MARKET_DIR)
    ? readdirSync(MARKET_DIR)
        .filter((name) => /^\d{4}-\d{2}-\d{2}\.md$/u.test(name))
        .map((name) => name.replace(/\.md$/u, ""))
        .sort()
        .reverse()
    : [];

/**
 * 주간 전망(src/news/market/YYYY-MM-DD 주간.md)의 파일 이름(확장자 제외)을 최신순으로 돌려줍니다.
 * 일일 증시 전망과 파일 이름이 달라 marketDates와 른로 읽습니다.
 */
export const weeklyDates = (): string[] =>
  existsSync(MARKET_DIR)
    ? readdirSync(MARKET_DIR)
        .filter((name) => /^\d{4}-\d{2}-\d{2} 주간\.md$/u.test(name))
        .map((name) => name.replace(/\.md$/u, ""))
        .sort()
        .reverse()
    : [];

/**
 * 증시 전망 카테고리에 함께 싣는 페이지 이름을 최신순으로 돌려줍니다.
 * 일일 페이지(YYYY-MM-DD)와 주간 페이지(YYYY-MM-DD 주간)를 날짜 순서로 섞습니다.
 */
export const marketPageNames = (): string[] => [...marketDates(), ...weeklyDates()].sort().reverse();

/**
 * 메인 페이지의 증시 전망 구획에 넣을 문구를 날짜별 페이지 본문에서 읽어 만듭니다.
 * 페이지 형식이 어긋나면 잘못된 요약이 나가지 않도록 오류를 냅니다.
 */
export const marketSummary = (
  date: string,
  text = readFileSync(new URL(`${date}.md`, MARKET_DIR), "utf8"),
) => {
  const usClose = /(\d{1,2}\/\d{1,2}\([일월화수목금토]\)) 뉴욕 정규장 종가 기준/u.exec(text)?.[1];
  const changes = [
    ...text.matchAll(/market-card__name">([^<]+)<[\s\S]*?market-card__change">[^(]*\(([-+][\d.]+%)\)/gu),
  ];
  if (!usClose || changes.length !== 4) {
    throw new Error(`${date} 증시 전망 페이지에서 메인 요약을 읽지 못했습니다`);
  }

  const [year, month, day] = date.split("-").map(Number);
  const weekday = WEEKDAYS[new Date(Date.UTC(year, month - 1, day)).getUTCDay()];

  return {
    link: `/news/market/${date}.html`,
    title: `${date} 증시 전망`,
    briefing: `${year}년 ${month}월 ${day}일(${weekday}) 브리핑입니다. 미국은 ${usClose} 뉴욕 정규장 종가 기준입니다.`,
    changes: changes.map(([, name, change]) => `${decodeHtml(name)} ${change}`).join(" · "),
  };
};
