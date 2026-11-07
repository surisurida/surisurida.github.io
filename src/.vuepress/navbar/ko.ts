import { navbar } from "vuepress-theme-hope";

import { marketDates } from "../market.js";
import { newsDates } from "../news.js";

const [latestMarketDate] = marketDates();

export const koNavbar = navbar([
  // 카테고리를 누르면 가장 최근 날짜 페이지로 이동하고, 그 카테고리의 어느 날짜에서든 활성 표시됩니다.
  // 증시 전망은 배포 때 만드는 페이지라 아직 없으면 메뉴에서 뺍니다.
  ...(latestMarketDate
    ? [{ text: "증시 전망", icon: "chart-line", link: `/news/market/${latestMarketDate}`, activeMatch: "^/news/market/" }]
    : []),
  { text: "AI 뉴스", icon: "brain", link: `/news/ai/${newsDates("ai")[0]}`, activeMatch: "^/news/ai/" },
  { text: "로봇 뉴스", icon: "robot", link: `/news/robot/${newsDates("robot")[0]}`, activeMatch: "^/news/robot/" },
]);
