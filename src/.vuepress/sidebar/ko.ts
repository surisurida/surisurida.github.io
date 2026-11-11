import { sidebar } from "vuepress-theme-hope";

import { marketPageNames } from "../market.js";
import { newsDates } from "../news.js";

// 일일(YYYY-MM-DD)과 주간(YYYY-MM-DD 주간) 페이지를 같은 증시 전망 목록에 싣습니다.
const marketPages = marketPageNames();
const aiDates = newsDates("ai");
const robotDates = newsDates("robot");

export const koSidebar = sidebar({
  "/": [
    "",
    {
      text: "뉴스",
      icon: "newspaper",
      prefix: "news/",
      // 카테고리를 누르면 가장 최근 날짜 페이지로 이동하고, 아래에 날짜별 페이지를 최신순으로 보여줍니다
      children: [
        // 증시 전망과 뉴스는 로컬에서 만드는 페이지라 아직 없으면 메뉴에서 뺍니다
        ...(marketPages.length > 0
          ? [
              {
                text: "증시 전망",
                icon: "chart-line",
                prefix: "market/",
                link: `market/${marketPages[0]}`,
                collapsible: true,
                children: marketPages,
              },
            ]
          : []),
        ...(aiDates.length > 0
          ? [{ text: "AI", icon: "brain", prefix: "ai/", link: `ai/${aiDates[0]}`, collapsible: true, children: aiDates }]
          : []),
        ...(robotDates.length > 0
          ? [
              {
                text: "로봇",
                icon: "robot",
                prefix: "robot/",
                link: `robot/${robotDates[0]}`,
                collapsible: true,
                children: robotDates,
              },
            ]
          : []),
      ],
    },
  ],
});
