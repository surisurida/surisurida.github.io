# surisurida.github.io

수리의 홈페이지 — [VuePress 2](https://vuejs.press/) + [vuepress-theme-hope](https://theme-hope.vuejs.press/)로 만든 정적 사이트입니다.
`main` 브랜치에 푸시하면 GitHub Actions가 빌드해서 GitHub Pages(<https://surisurida.github.io>)에 배포합니다.

## 요구 사항

- Node.js 24
- pnpm (버전은 `package.json`의 `packageManager` 필드에 고정되어 있음 — `corepack enable`로 맞추면 편합니다)
- [uv](https://docs.astral.sh/uv/) — 뉴스 수집 스크립트(Python) 실행용. Python과 패키지는 uv가 알아서 받습니다.

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
| `pnpm news:update` | AI·로봇 뉴스를 수집해 `data/news/`에 쌓고 `src/news/`를 다시 생성 (`uv run scripts/fetch_news.py`와 같음) |

## 디렉터리 구조

```
.
├── .github/workflows/deploy-docs.yml   # GitHub Pages 배포 워크플로
├── scripts/fetch_news.py               # 뉴스 수집 스크립트 (uv로 실행)
├── src/                                # 사이트 소스 (VuePress 루트)
│   ├── README.md                       # 홈페이지 (/)
│   ├── news/                           # 뉴스 페이지 — 스크립트가 생성 (ai/, robot/ 아래 날짜별)
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
메뉴에 노출하려면 `src/.vuepress/navbar/ko.ts`, `src/.vuepress/sidebar/ko.ts`를 수정하세요.
frontmatter와 마크다운 확장 문법은 [테마 문서](https://theme-hope.vuejs.press/guide/)를 참고하세요.

## 뉴스 페이지

AI·로봇 뉴스 링크를 카테고리별·날짜별로 모아 둡니다. `scripts/fetch_news.py`가 국내외 매체의 RSS를 읽어
마크다운을 생성하므로 `src/news/`의 파일은 직접 고치지 말고 스크립트를 다시 실행하세요.

```bash
uv run scripts/fetch_news.py   # 또는 pnpm news:update
```

| 파일 | 내용 |
| --- | --- |
| `data/news/ai.json`, `robot.json` | 수집한 기사 저장소 — 페이지는 이 데이터로 만듭니다 |
| `src/news/ai/YYYY-MM-DD.md` | 그날(한국 시간) 나온 AI 뉴스 (국내·해외) |
| `src/news/robot/YYYY-MM-DD.md` | 그날 나온 로봇 뉴스 |
| `src/.vuepress/news.ts` | 메뉴에 넣을 날짜 페이지 목록을 읽는 함수 |

- 카테고리 첫 페이지는 따로 없습니다. 메뉴에서 AI·로봇을 누르거나 `/news/ai/`로 들어오면 가장 최근 날짜 페이지로 이동합니다.
- 메뉴의 날짜 목록은 빌드(또는 개발 서버 시작) 때 `src/news/<카테고리>/`의 파일을 읽어 만듭니다.
  개발 서버 실행 중에 뉴스를 새로 수집했다면 서버를 다시 시작해야 메뉴에 반영됩니다.
- 실행할 때마다 피드의 최근 7일 기사 중 처음 보는 기사만 `data/news/`에 추가하고, 날짜별 페이지를 다시 만듭니다.
- 해외 기사 제목은 비공식 Google 번역으로 한국어로 옮겨 함께 저장합니다(제목에 마우스를 올리면 원문).
  번역이 막히면 원문 제목을 쓰고 다음 실행 때 다시 시도합니다.
- 기사 대표 이미지를 제목 왼쪽에 보여 줍니다(배치는 `src/.vuepress/styles/index.scss`). 피드에 이미지가 없으면
  원문 페이지의 `og:image`를 한 번만 찾아 저장합니다. 찾은 이미지는 실제로 열리는지(https, 이미지 응답) 확인해서
  깨지는 이미지는 넣지 않습니다. 차단되지 않도록 사이트마다 1초 간격으로 요청하고,
  오류가 나면 그 사이트는 다음 실행 때 다시 시도합니다.
- Google 뉴스 RSS는 `news.google.com` 링크만 주므로, Google의 비공식 내부 API로 원문 주소를 알아내 링크를 바꾸고
  이미지를 찾습니다(한 번 실행에 최신 150건까지, 1초 간격). 막히거나 실패하면 Google 링크를 그대로 쓰고(이미지 없음)
  다음 실행 때 이어서 시도합니다.
- 피드에는 최근 며칠치만 남기 때문에, **날짜별 페이지를 계속 쌓으려면 스크립트를 실행한 뒤
  `data/news/`와 `src/news/`를 커밋해야 합니다.** 배포 워크플로는 수집만 하고 커밋하지 않습니다.
- 일부 출처가 실패해도 나머지로 진행합니다. 한 카테고리 전체가 실패하면 아무 파일도 바꾸지 않습니다.

## 배포

`main`에 푸시하거나 Actions 탭에서 **Deploy Docs**를 수동 실행하면 다음이 진행됩니다.
최신 뉴스를 반영하기 위해 매일 06:00, 12:00, 18:00(KST)에도 자동으로 실행됩니다.

1. `pnpm install --frozen-lockfile`
2. `pnpm test`
3. `uv run scripts/fetch_news.py` — 최신 뉴스 수집 (실패해도 저장소의 기존 뉴스 페이지로 계속 진행)
4. `pnpm docs:build`
5. `src/.vuepress/dist`를 GitHub Pages에 업로드·배포

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
