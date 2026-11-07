import { defineUserConfig } from "vuepress";

import { marketDates, marketSummary } from "./market.js";
import theme from "./theme.js";

const [latestMarketDate] = marketDates();

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

  // 메인 페이지 요약과 /news/market/ 이동은 빌드 때 최신 증시 전망 페이지에서 만듭니다. 페이지가 없으면 나오지 않습니다.
  extendsPage: (page) => {
    if (!latestMarketDate) return;
    if (page.path === "/") {
      page.frontmatter.market = marketSummary(latestMarketDate);
    }
    if (page.path === `/news/market/${latestMarketDate}.html`) {
      page.frontmatter.redirectFrom = "/news/market/";
    }
  },

  // Enable it with pwa
  // shouldPrefetch: false,
});
