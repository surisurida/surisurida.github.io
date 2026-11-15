import { navbar } from "vuepress-theme-hope";

import { latestMarketPage } from "../market.js";
import { newsDates } from "../news.js";

// 일일·주간 증시 전망 중 마지막으로 만든 페이지 하나를 메뉴 링크로 겁니다.
const latestMarket = latestMarketPage();
const [latestAiDate] = newsDates("ai");
const [latestRobotDate] = newsDates("robot");

export const koNavbar = navbar([
  // 카테고리를 누르면 가장 최근 날짜 페이지로 이동하고, 그 카테고리의 어느 날짜에서든 활성 표시됩니다.
  // 증시 전망과 뉴스는 로컬에서 만드는 페이지라 아직 없으면 메뉴에서 뺍니다.
  ...(latestMarket
    ? [
        {
          text: "증시 전망",
          icon: "chart-line",
          link: `/news/market/${latestMarket.name}`,
          activeMatch: "^/news/market/",
        },
      ]
    : []),
  ...(latestAiDate
    ? [{ text: "AI 뉴스", icon: "brain", link: `/news/ai/${latestAiDate}`, activeMatch: "^/news/ai/" }]
    : []),
  ...(latestRobotDate
    ? [{ text: "로봇 뉴스", icon: "robot", link: `/news/robot/${latestRobotDate}`, activeMatch: "^/news/robot/" }]
    : []),
]);
