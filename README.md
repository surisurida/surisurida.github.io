# surisurida.github.io

수리의 홈페이지 — [VuePress 2](https://vuejs.press/) + [vuepress-theme-hope](https://theme-hope.vuejs.press/)로 만든 정적 사이트입니다.
`main` 브랜치에 푸시하면 GitHub Actions가 빌드해서 GitHub Pages(<https://surisurida.github.io>)에 배포합니다.

## 요구 사항

- Node.js 26
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
├── scripts/
│   ├── fetch_news.py                   # 뉴스 수집 스크립트 (uv로 실행)
│   ├── write_market_brief.py           # 증시 전망 작성 스크립트 (uv로 실행)
│   └── market_brief/                   # 증시 전망 작성·법률 검토 프롬프트와 형식 본보기
├── src/                                # 사이트 소스 (VuePress 루트)
│   ├── README.md                       # 홈페이지 (/)
│   ├── news/                           # 뉴스·증시 전망 페이지 — 스크립트가 생성 (ai/, robot/, market/ 아래 날짜별)
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

## 증시 전망 페이지

미국 증시 테마와 연계되는 한국 증시 테마를 정리합니다. AI·로봇 뉴스처럼 배포 때 `src/news/market/YYYY-MM-DD.md`를 만들고, 커밋하지 않는 일회성 페이지입니다.

- 구성은 ① 미국 지수 카드 → ② 일정 체크포인트 → ③ 미국·한국 테마 연계 표 → 면책 조항 순서로 고정합니다.
- 메뉴, 메인 페이지 요약, `/news/market/` 이동은 빌드 때 이 폴더의 최신 페이지로 만듭니다. 페이지가 없으면 메뉴와 메인에서 빠집니다.
- `scripts/market_brief/2026-11-06.md`는 사이트에 나오지 않는 형식 본보기입니다. 작성할 때 참고하고 `pnpm test`도 함께 검사합니다.
- `tests/market.test.ts`가 구성, 카드 계산, 미국 기준일, 허용 태그와 링크, 게시 금지 표현을 검사합니다. 문구와 형식만 거르는 검사이므로 법률 검토를 대신하지 않습니다.

### 자동 작성

`scripts/write_market_brief.py`가 배포 워크플로의 뉴스 수집 다음 단계에서 실행됩니다. 처음 한 번은 저장소 **Settings → Secrets and variables → Actions**에 다음 중 하나를 등록해야 합니다. 없으면 증시 전망 없이 배포합니다.

| 시크릿 | 인증 방식 | 비용 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Claude Console API 키 | 사용한 만큼 API 요금 |
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude setup-token`으로 만든 토큰 (1년 유효) | Claude 구독 사용량 |

작성에 비용이 들어 한국 평일 07:30 이후 첫 배포에서 하루 한 번만 씁니다. `cron` 값이 아니라 실제 실행 시각으로 판단하므로 `cron`을 바꿔도 스크립트는 그대로 둡니다. 주말, 07:30 전, 그날의 나머지 배포는 Actions 캐시에서 되살린 페이지를 그대로 씁니다. 새 페이지가 통과하면 이전 페이지는 지우고, 4일이 지난 페이지는 내립니다.

강제로 쓰려면 저장소 **Settings → Secrets and variables → Actions**의 **Variables** 탭에 `MARKET_BRIEF_FORCE`를 `Y`로 넣고 **Deploy Docs**를 실행합니다. 주말이나 07:30 전이어도, 오늘 페이지가 이미 있어도 새로 쓰며, 새 페이지가 통과하지 못하면 기존 페이지를 그대로 둡니다. 값이 저절로 돌아가지 않고 `Y`인 동안은 예약 실행과 푸시까지 모든 배포에서 작성해 비용이 드니, 실행이 끝나면 `N`으로 되돌리세요. `N`이거나 변수가 없으면 평소대로 동작합니다.

작성 순서는 다음과 같습니다.

1. **작성** — Claude Code가 `scripts/market_brief/write.md`대로 웹을 조사해 새 페이지 하나를 씁니다.
2. **검사** — 새 페이지 외의 변경이 없는지 확인하고 `pnpm test`를 실행합니다.
3. **법률 검토** — 도구 없이 페이지 내용만 보는 별도 실행이 `scripts/market_brief/review.md` 기준으로 판정합니다.

결과에 따라 배포가 달라집니다.

| 상황 | 결과 |
| --- | --- |
| 모두 통과 | 새 페이지로 배포합니다. |
| 시크릿 없음, 명령 격리 준비 실패, API 오류, 핵심 수치를 확인하지 못함, 법률 검토 결과를 받지 못함 | 새 페이지를 버리고 직전 페이지로 배포합니다. 실행에는 경고만 남으며, Claude Code가 결과를 내지 못했으면 경고에 종료 코드와 오류 문구가 함께 나옵니다. |
| `pnpm test` 실패, 새 페이지 외의 변경, 법률 검토 `violation` | 새 페이지를 버리고 배포를 중단합니다. 실패 알림은 GitHub가 cron을 마지막으로 바꾼 사용자에게 보냅니다. |

알아 둘 점입니다.

- 단계별 판정과 추정 비용은 실행 요약에 남습니다. 모델, Claude Code 버전, 실행당 비용 상한은 스크립트 맨 위 상수에 있습니다.
- 작성 실행은 웹 자료를 읽으므로 `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`으로 하위 명령에서 토큰을 숨기고 격리합니다. Linux에서는 여기에 bubblewrap과 socat이 필요해, 스크립트가 작성할 때만 러너에 없는 것을 설치하고 Ubuntu의 사용자 네임스페이스 제한을 풉니다(공식 `claude-code-action`과 같은 방법). 격리 시험이 실패하면 비용을 쓰기 전에 멈춥니다.
- Yahoo는 약관이 자동 수집을 금지하고 Finviz도 제한한다고 알려져 있어 직접 가져오기를 막았습니다(`BLOCKED_FETCHES`). 그래서 표가 10개보다 좁아질 수 있습니다.
- 법률 검토는 무료·일방향 사이트라는 전제에서 합니다. 광고, 유료 회원, 댓글을 붙이면 `review.md`의 전제와 법률 판단을 먼저 다시 확인하세요.

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
| `data/news/home.md` | 메인 페이지에 넣을 카테고리별 최신 뉴스 구획 — `src/README.md`가 불러옵니다 |
| `src/.vuepress/news.ts` | 메뉴에 넣을 날짜 페이지 목록을 읽는 함수 |

- 카테고리 첫 페이지는 따로 없습니다. 메뉴에서 AI·로봇을 누르거나 `/news/ai/`로 들어오면 가장 최근 날짜 페이지로 이동합니다.
- 메인 페이지에는 카테고리별로 가장 최근 날짜의 기사를 최신순으로 5건까지 보여 줍니다. 그날 기사가 5건보다 적으면 있는 만큼만 나옵니다.
  스크립트를 한 번도 실행하지 않아 `data/news/home.md`가 없으면 메인 페이지에 `File not found`가 표시됩니다.
- 메뉴의 날짜 목록은 빌드(또는 개발 서버 시작) 때 `src/news/<카테고리>/`의 파일을 읽어 만듭니다.
  개발 서버 실행 중에 뉴스를 새로 수집했다면 서버를 다시 시작해야 메뉴에 반영됩니다.
- 실행할 때마다 피드의 최근 7일 기사 중 처음 보는 기사만 `data/news/`에 추가하고, 날짜별 페이지를 다시 만듭니다.
- 페이지에는 기사 제목, 원문 링크, 출처, 시간만 넣습니다. 기사 본문과 대표 이미지는 가져오지 않습니다.
- 해외 기사 제목은 번역하지 않고 피드의 원문 제목을 그대로 보여 줍니다.
- Google 뉴스 RSS는 `news.google.com` 링크만 주므로, Google의 비공식 내부 API로 원문 주소를 알아내 링크를 바꿉니다
  (한 번 실행에 최신 150건까지, 1초 간격). 막히거나 실패하면 Google 링크를 그대로 쓰고 다음 실행 때 이어서 시도합니다.
- 피드에는 최근 며칠치만 남기 때문에, **날짜별 페이지를 계속 쌓으려면 스크립트를 실행한 뒤
  `data/news/`와 `src/news/`를 커밋해야 합니다.** 배포 워크플로는 수집만 하고 커밋하지 않습니다.
- 일부 출처가 실패해도 나머지로 진행합니다. 한 카테고리 전체가 실패하면 아무 파일도 바꾸지 않습니다.

## 배포

`main`에 푸시하거나 Actions 탭에서 **Deploy Docs**를 수동 실행하면 다음이 진행됩니다.
최신 뉴스를 반영하기 위해 `cron`으로 예약 실행도 합니다. GitHub 예약 실행은 몇 시간씩 늦거나 건너뛸 수 있어, `cron`은 원하는 시각보다 앞당겨 둔 값이고 지연이 달라지면 조정합니다.

1. `pnpm install --frozen-lockfile`
2. `pnpm test`
3. `uv run scripts/fetch_news.py` — 최신 뉴스 수집 (실패해도 저장소의 기존 뉴스 페이지로 계속 진행)
4. `uv run scripts/write_market_brief.py` — 증시 전망 작성 (위 [자동 작성](#자동-작성) 참고, 위반을 찾으면 배포 중단)
5. `pnpm test` — 증시 전망 페이지까지 포함해 다시 검사
6. `pnpm docs:build`
7. `src/.vuepress/dist`를 GitHub Pages에 업로드·배포

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
