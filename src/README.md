---
home: true
icon: house
heroImage: https://pjy.kr/logo.svg
heroImageStyle:
  max-height: 10rem
bgImage: https://pjy.kr/lowpoly-light.webp
bgImageDark: https://pjy.kr/lowpoly-dark.webp
bgImageStyle:
  background-attachment: fixed
heroText: 뉴스 허브
tagline: 수리 페이지에서 제공하는 정보는 AI로 수집하고 있습니다.

footer: <a href="/email.html">이메일무단수집거부</a> · <a href="/privacy.html">개인정보처리방침</a>
copyright: © 수리 2026
containerClass: news-page
---

<template v-if="$frontmatter.market">

## 증시 전망

{{ $frontmatter.market.briefing }} <RouteLink :to="$frontmatter.market.link">전체 보기</RouteLink>

- <RouteLink :to="$frontmatter.market.link">{{ $frontmatter.market.title }}</RouteLink>
  <small>{{ $frontmatter.market.changes }}</small>

</template>

<!-- @include: ./.vuepress/home.md -->

<div class="contact-box">

수리 페이지를 찾아주셔서 감사합니다! 글에 대한 의견이나 궁금한 점이 있으시다면 언제든 편하게 연락해 주세요.

- 문의 채널 : ![문의 이메일 주소](/email-light-text.svg#light)![문의 이메일 주소](/email-dark-text.svg#dark)

</div>
