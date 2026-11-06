import { navbar } from "vuepress-theme-hope";

import { marketDates } from "../market.js";
import { newsDates } from "../news.js";

export const koNavbar = navbar([
  // 카테고리를 누르면 가장 최근 날짜 페이지로 이동하고, 그 카테고리의 어느 날짜에서든 활성 표시됩니다.
  { text: "증시 전망", icon: "chart-line", link: `/market/${marketDates()[0]}`, activeMatch: "^/market/" },
  { text: "AI 뉴스", icon: "brain", link: `/news/ai/${newsDates("ai")[0]}`, activeMatch: "^/news/ai/" },
  { text: "로봇 뉴스", icon: "robot", link: `/news/robot/${newsDates("robot")[0]}`, activeMatch: "^/news/robot/" },
]);
