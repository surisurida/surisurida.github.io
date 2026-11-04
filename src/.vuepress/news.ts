import { readdirSync } from "node:fs";

/**
 * 뉴스 카테고리(src/news/<category>/)의 날짜별 페이지 이름(YYYY-MM-DD)을 최신순으로 돌려줍니다.
 * 날짜 페이지는 scripts/fetch_news.py가 만들고, 메뉴는 빌드(또는 개발 서버 시작) 시점의 파일 목록을 씁니다.
 */
export const newsDates = (category: string): string[] =>
  readdirSync(new URL(`../news/${category}/`, import.meta.url))
    .filter((name) => /^\d{4}-\d{2}-\d{2}\.md$/u.test(name))
    .map((name) => name.replace(/\.md$/u, ""))
    .sort()
    .reverse();
