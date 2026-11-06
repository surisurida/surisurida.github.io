import { sidebar } from "vuepress-theme-hope";

import { marketDates } from "../market.js";
import { newsDates } from "../news.js";

const marketPages = marketDates();
const aiDates = newsDates("ai");
const robotDates = newsDates("robot");

export const koSidebar = sidebar({
  "/": [
    "",
    {
      text: "증시 전망",
      icon: "chart-line",
      prefix: "market/",
      link: `market/${marketPages[0]}`,
      collapsible: true,
      children: marketPages,
    },
    {
      text: "뉴스",
      icon: "newspaper",
      prefix: "news/",
      // 카테고리를 누르면 가장 최근 날짜 페이지로 이동하고, 아래에 날짜별 페이지를 최신순으로 보여준다
      children: [
        { text: "AI", icon: "brain", prefix: "ai/", link: `ai/${aiDates[0]}`, collapsible: true, children: aiDates },
        {
          text: "로봇",
          icon: "robot",
          prefix: "robot/",
          link: `robot/${robotDates[0]}`,
          collapsible: true,
          children: robotDates,
        },
      ],
    },
  ],
});
