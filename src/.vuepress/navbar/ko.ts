import { navbar } from "vuepress-theme-hope";

import { marketDates } from "../market.js";
import { newsDates } from "../news.js";

const [latestMarketDate] = marketDates();
const [latestAiDate] = newsDates("ai");
const [latestRobotDate] = newsDates("robot");

export const koNavbar = navbar([
  // 카테고리를 누르면 가장 최근 날짜 페이지로 이동하고, 그 카테고리의 어느 날짜에서든 활성 표시됩니다.
  // 증시 전망과 뉴스는 로컬에서 만드는 페이지라 아직 없으면 메뉴에서 뺍니다.
  ...(latestMarketDate
    ? [{ text: "증시 전망", icon: "chart-line", link: `/news/market/${latestMarketDate}`, activeMatch: "^/news/market/" }]
    : []),
  ...(latestAiDate
    ? [{ text: "AI 뉴스", icon: "brain", link: `/news/ai/${latestAiDate}`, activeMatch: "^/news/ai/" }]
    : []),
  ...(latestRobotDate
    ? [{ text: "로봇 뉴스", icon: "robot", link: `/news/robot/${latestRobotDate}`, activeMatch: "^/news/robot/" }]
    : []),
]);
