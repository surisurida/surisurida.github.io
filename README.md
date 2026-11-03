# surisurida.github.io

수리의 홈페이지 — [VuePress 2](https://vuejs.press/) + [vuepress-theme-hope](https://theme-hope.vuejs.press/)로 만든 정적 사이트입니다.
`main` 브랜치에 푸시하면 GitHub Actions가 빌드해서 GitHub Pages(<https://surisurida.github.io>)에 배포합니다.

## 요구 사항

- Node.js 24
- pnpm (버전은 `package.json`의 `packageManager` 필드에 고정되어 있음 — `corepack enable`로 맞추면 편합니다)

## 시작하기

```bash
pnpm install       # 의존성 설치
pnpm docs:dev      # 개발 서버 실행 (기본 http://localhost:8080)
```

## 스크립트

| 명령어 | 설명 |
| --- | --- |
| `pnpm docs:dev` | 개발 서버 실행 (핫 리로드) |
| `pnpm docs:clean-dev` | 캐시를 지우고 개발 서버 실행 — 화면이 이상하게 갱신될 때 사용 |
| `pnpm docs:build` | 프로덕션 빌드, 결과물은 `src/.vuepress/dist` |
| `pnpm docs:update-package` | VuePress·테마 관련 패키지 업데이트 (`vp-update`) |

## 디렉터리 구조

```
.
├── .github/workflows/deploy-docs.yml   # GitHub Pages 배포 워크플로
├── src/                                # 사이트 소스 (VuePress 루트)
│   ├── README.md                       # 홈페이지 (/)
│   ├── portfolio.md                    # /portfolio.html
│   ├── guide/  demo/                   # 문서 페이지
│   └── .vuepress/
│       ├── config.ts                   # 사이트 설정 (제목, 언어, base 등)
│       ├── theme.ts                    # 테마 설정 (작성자, 로고, 마크다운 기능, 플러그인)
│       ├── navbar/                     # 상단 내비게이션
│       ├── sidebar/                    # 사이드바
│       ├── styles/                     # 커스텀 스타일 (SCSS)
│       └── public/                     # 그대로 복사되는 정적 파일 (이미지, 아이콘 등)
├── package.json
└── pnpm-workspace.yaml                 # 빌드 스크립트 허용 목록 (esbuild, @parcel/watcher)
```

> 루트의 이 `README.md`는 저장소 설명용이고, 사이트 홈페이지는 `src/README.md`입니다.

## 글 작성

`src/` 아래에 마크다운 파일을 추가하면 경로가 그대로 URL이 됩니다 (`src/guide/foo.md` → `/guide/foo.html`).
메뉴에 노출하려면 `src/.vuepress/navbar/en.ts`, `src/.vuepress/sidebar/en.ts`를 수정하세요.
frontmatter와 마크다운 확장 문법은 [테마 문서](https://theme-hope.vuejs.press/guide/)를 참고하세요.

## 배포

`main`에 푸시하거나 Actions 탭에서 **Deploy Docs**를 수동 실행하면 다음이 진행됩니다.

1. `pnpm install --frozen-lockfile`
2. `pnpm docs:build`
3. `src/.vuepress/dist`를 GitHub Pages에 업로드·배포

처음 한 번은 저장소 **Settings → Pages → Source**를 **GitHub Actions**로 설정해야 합니다.

## TODO — 템플릿 기본값 정리

아직 vuepress-theme-hope 데모 템플릿의 값이 남아 있습니다.

- [ ] `config.ts`: `title`, `description`, `lang`(`ko-KR`)
- [ ] `theme.ts`: `hostname`, `author`, `logo`, `repo`, `footer`
- [ ] `theme.ts`: 데모용 Giscus 댓글 설정 → 본인 저장소로 교체하거나 제거 (데모 값은 테스트 전용)
- [ ] `theme.ts`: 데모용 암호화 페이지 설정(`/demo/encrypt.html`, 비밀번호 1234) 제거
- [ ] `src/demo/`, `src/guide/` 예제 페이지 정리

## 라이선스

MIT
