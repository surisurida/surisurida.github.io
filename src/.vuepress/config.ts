import { defineUserConfig } from "vuepress";

import { latestMarketPage, marketDates, marketSummary, weeklySummary } from "./market.js";
import theme from "./theme.js";

const [latestMarketDate] = marketDates();
const latestPage = latestMarketPage();

export default defineUserConfig({
  base: "/",

  locales: {
    "/": {
      lang: "ko-KR",
      title: "수리 페이지",
      description: "수리가 관리하는 GitHub 페이지입니다.",
    },
  },

  theme,

  // 메인 페이지 요약은 일일·주간 중 마지막으로 만든 페이지 하나로 만듭니다.
  // /news/market/ 이동은 일일 페이지가 맡습니다(주간 페이지의 경로에 공백이 있어 redirectFrom을 쓰지 않습니다).
  extendsPage: (page) => {
    if (page.path === "/" && latestPage) {
      page.frontmatter.market =
        latestPage.kind === "weekly" ? weeklySummary(latestPage.name) : marketSummary(latestPage.name);
    }
    if (latestMarketDate && page.path === `/news/market/${latestMarketDate}.html`) {
      page.frontmatter.redirectFrom = "/news/market/";
    }
  },

  // Enable it with pwa
  // shouldPrefetch: false,
});
