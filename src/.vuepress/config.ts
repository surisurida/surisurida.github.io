import { defineUserConfig } from "vuepress";

import theme from "./theme.js";

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

  // Enable it with pwa
  // shouldPrefetch: false,
});
