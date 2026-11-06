import { readdirSync } from "node:fs";

/**
 * 증시 전망(src/market/)의 날짜별 페이지 이름(YYYY-MM-DD)을 최신순으로 돌려줍니다.
 * 뉴스와 달리 직접 작성해 저장소에 커밋하는 페이지이며, 메뉴는 빌드 시점의 파일 목록을 씁니다.
 */
export const marketDates = (): string[] =>
  readdirSync(new URL("../market/", import.meta.url))
    .filter((name) => /^\d{4}-\d{2}-\d{2}\.md$/u.test(name))
    .map((name) => name.replace(/\.md$/u, ""))
    .sort()
    .reverse();
