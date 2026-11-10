# surisurida.github.io

수리의 홈페이지 — [VuePress 2](https://vuejs.press/) + [vuepress-theme-hope](https://theme-hope.vuejs.press/)로 만든 정적 사이트입니다.
뉴스 수집과 증시 전망 작성은 로컬 PC의 스케줄러가 수행하고, 생성된 `src/news/`·`src/.vuepress/home.md`를 커밋해 `main`에 푸시합니다. GitHub Actions는 푸시된 소스를 빌드해 GitHub Pages(<https://surisurida.github.io>)에 배포합니다.
`scripts/`·`tests/`·`data/`는 로컬 전용이라 저장소에 커밋하지 않습니다.

## 요구 사항

- Node.js 26
- pnpm (버전은 `package.json`의 `packageManager` 필드에 고정되어 있음 — `corepack enable`로 맞추면 편합니다)
- [uv](https://docs.astral.sh/uv/) — 뉴스 수집·증시 전망 스크립트(Python) 실행용. Python과 패키지는 uv가 알아서 받습니다.
- `DEEPSEEK_API_KEY` — 로컬 증시 전망 작성용 환경 변수
- Git push 권한 — 로컬 스케줄러가 `main`에 푸시합니다
- Windows 작업 스케줄러 — 특정 시각 자동 실행용 (선택)

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
| `pnpm news:update` | AI·로봇 뉴스를 수집해 `src/news/`와 `src/.vuepress/home.md`를 갱신 (`uv run scripts/fetch_news.py`와 같음, `data/news/`는 로컬에만 저장) |
| `pnpm market:update` | 증시 전망만 작성 (`uv run scripts/write_market_brief.py`와 같음) |
| `pnpm update:local` | 뉴스 수집 → 증시 전망 작성 → 테스트 → `src/news/`·`src/.vuepress/home.md` 커밋 → `main` 푸시 |
| `pnpm test` | 로컬 테스트 (`tests/`는 저장소에 커밋하지 않음) |

## 디렉터리 구조

```
.
├── .github/workflows/deploy-docs.yml   # 푸시된 소스를 GitHub Pages로 배포
├── data/news/                          # 수집한 기사 데이터 — 로컬 전용, 커밋하지 않음
├── scripts/                            # 로컬 전용 — 커밋하지 않음
│   ├── fetch_news.py                   # 뉴스 수집 스크립트 (uv로 실행)
│   ├── write_market_brief.py           # 증시 전망 작성 스크립트 (uv로 실행)
│   ├── run_local_update.ps1            # 로컬 수집·검사·커밋·푸시
│   └── market_brief/                   # 증시 전망 작성·법률 검토 프롬프트와 형식 본보기
├── tests/                              # 로컬 전용 — 커밋하지 않음
├── logs/                               # 로컬 실행 로그 — 커밋하지 않음
├── src/                                # 사이트 소스 (VuePress 루트)
│   ├── README.md                       # 홈페이지 (/)
│   ├── news/                           # 뉴스·증시 전망 페이지 — 스크립트가 생성하고 커밋 (ai/, robot/, market/ 아래 날짜별)
│   └── .vuepress/
│       ├── home.md                     # 메인 페이지 뉴스 구획 — 스크립트가 생성하고 커밋
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

미국 증시 테마와 연계되는 한국 증시 테마를 정리합니다. 로컬 스케줄러가 `src/news/market/YYYY-MM-DD.md`를 만들고 커밋합니다. 새 페이지가 통과하면 이전 페이지만 남기므로 저장소에는 최신 페이지만 유지됩니다.

- 구성은 ① 미국 지수 카드 → ② 일정 체크포인트 → ③ 미국·한국 테마 연계 표 → 면책 조항 순서로 고정합니다.
- 메뉴, 메인 페이지 요약, `/news/market/` 이동은 빌드 때 이 폴더의 최신 페이지로 만듭니다. 페이지가 없으면 메뉴와 메인에서 빠집니다.
- 로컬에 있는 `scripts/market_brief/2026-11-06.md`는 사이트에 나오지 않는 형식 본보기입니다. 작성할 때 참고하고 `pnpm test`도 함께 검사합니다.
- `tests/market.test.ts`가 구성, 카드 계산, 미국 기준일, 허용 태그와 링크, 게시 금지 표현을 검사합니다. 문구와 형식만 거르는 검사이므로 법률 검토를 대신하지 않습니다.

### 자동 작성

`scripts/write_market_brief.py`는 로컬 스케줄러(`scripts/run_local_update.ps1`)가 뉴스 수집 다음에 실행합니다. GitHub Actions에서는 실행하지 않습니다. 로컬 Windows 환경 변수 `DEEPSEEK_API_KEY`가 필요합니다.

| 환경 변수 | 설명 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek Platform에서 발급한 API 키 (필수) |
| `DEEPSEEK_MODEL` | 사용할 모델. 없으면 `deepseek-flash` |

`DEEPSEEK_API_KEY`는 현재 터미널이 아니라 **Windows 사용자 환경 변수**로 설정해야 작업 스케줄러에서도 보입니다.

```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-...", "User")
```

설정 후 새 터미널과 VS Code를 다시 시작하세요.

DeepSeek API에는 내장 웹 검색이 없어, 스크립트가 `search_news`(Google News RSS), `fetch_url`(직접 본문 조회), `fetch_quotes`(CNBC 시세) 도구를 제공하고 모델이 도구를 호출해 자료를 조사합니다. 작성에 비용이 들어 한국 평일 07:30 이후 하루 한 번만 씁니다. 주말이나 07:30 전에는 작성하지 않습니다. 새 페이지가 통과하면 이전 페이지는 지우고, 4일이 지난 페이지는 내립니다.

강제로 쓰려면 `-Force`를 붙입니다. 주말이나 07:30 전이어도, 오늘 페이지가 이미 있어도 새로 씁니다. `--force`는 실제 API 비용을 쓰고, 성공하면 다른 증시 전망 페이지를 지웁니다.

```powershell
$env:DEEPSEEK_API_KEY = "..."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local_update.ps1 -Force
```

### 로컬에서 실행

API 키를 환경 변수로 넣고 스크립트를 직접 실행할 수 있습니다.

```powershell
$env:DEEPSEEK_API_KEY = "..."
uv run scripts/write_market_brief.py --force
```

기준 시각을 바꿔 시험하려면 `--now`를 함께 씁니다.

```powershell
uv run scripts/write_market_brief.py --force --now "2026-11-09 08:00"
```

뉴스 수집까지 포함해 커밋·푸시하려면 `pnpm update:local`을 실행합니다. 푸시 없이 커밋만 하려면 `-NoPush`를 붙입니다.

```powershell
pnpm update:local
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local_update.ps1 -NoPush
```

`pnpm update:local`은 `src/news/`와 `src/.vuepress/home.md`만 커밋합니다. 워크플로·README 등 다른 변경은 별도로 커밋하세요.

`--force`는 실제 API 비용을 쓰고, 성공하면 다른 증시 전망 페이지를 지웁니다. 모델을 바꾸려면 `DEEPSEEK_MODEL` 환경 변수를 지정합니다.

작성 순서는 다음과 같습니다.

1. **작성** — DeepSeek가 `scripts/market_brief/write.md`대로 `search_news`·`fetch_url`·`fetch_quotes` 도구로 자료를 조사해 새 페이지 하나를 `submit_page`로 제출합니다.
2. **검사** — 새 페이지 외의 변경이 없는지 확인하고 `pnpm test`를 실행합니다.
3. **법률 검토** — 도구 없이 페이지 내용만 보는 별도 DeepSeek 실행이 `scripts/market_brief/review.md` 기준으로 판정합니다.

결과에 따라 로컬 스케줄러의 동작이 달라집니다.

| 상황 | 결과 |
| --- | --- |
| 모두 통과 | 뉴스·증시 전망을 커밋하고 `main`에 푸시합니다. GitHub Actions가 빌드·배포합니다. |
| `DEEPSEEK_API_KEY` 없음, API 오류, 핵심 수치를 확인하지 못함, 법률 검토 결과를 받지 못함 | 증시 전망을 버리고 뉴스 변경만 커밋·푸시합니다. 실행 로그에 경고가 남습니다. |
| `pnpm test` 실패 | 커밋·푸시하지 않고 종료합니다. |
| 새 페이지 외의 변경, 법률 검토 `violation` | 증시 전망을 버리고 뉴스 변경만 커밋·푸시합니다. |

알아 둘 점입니다.

- 단계별 판정과 DeepSeek 토큰 사용량은 콘솔과 `logs/update-*.log`에 남습니다. 모델 기본값과 최대 출력 토큰은 스크립트 맨 위 상수에 있고, 모델은 `DEEPSEEK_MODEL` 환경 변수로 바꿀 수 있습니다.
- 작성 실행은 스크립트가 제공하는 `search_news`, `fetch_url`, `fetch_quotes` 도구로만 웹 자료를 읽습니다. API 키는 DeepSeek 요청에만 쓰고 `pnpm test`에는 넘기지 않습니다.
- Yahoo는 약관이 자동 수집을 금지하고 Finviz도 제한한다고 알려져 있어 `fetch_url` 도구가 막습니다. 그래서 표가 10개보다 좁아질 수 있습니다.
- 법률 검토는 무료·일방향 사이트라는 전제에서 합니다. 광고, 유료 회원, 댓글을 붙이면 `review.md`의 전제와 법률 판단을 먼저 다시 확인하세요.
- 로컬 스케줄러는 PC가 켜져 있어야 실행됩니다. 절전·종료 상태면 Windows 작업 스케줄러의 “컴퓨터 깨우기”와 “예약 시작 시간을 놓치면 가능한 한 빨리 실행”을 켜세요. Git 인증이 만료되면 푸시가 실패합니다.
- 푸시가 실패하면 커밋은 로컬에 남고, 다음 실행에서 다시 푸시합니다. 원격에 새 커밋이 있으면 먼저 `git pull`로 정리하세요.

## 뉴스 페이지

AI·로봇 뉴스 링크를 카테고리별·날짜별로 모아 둡니다. `scripts/fetch_news.py`가 국내외 매체의 RSS를 읽어
마크다운을 생성하므로 `src/news/`의 파일은 직접 고치지 말고 스크립트를 다시 실행하세요. 페이지와 메인 요약은 어제부터 현재까지의 기사만 반영합니다.

```bash
uv run scripts/fetch_news.py   # 또는 pnpm news:update
```

| 파일 | 내용 |
| --- | --- |
| `data/news/ai.json`, `robot.json` | 수집한 기사 저장소(로컬 전용) — 페이지는 이 데이터로 만듭니다 |
| `src/news/ai/YYYY-MM-DD.md` | 그날(한국 시간) 나온 AI 뉴스 (국내·해외) |
| `src/news/robot/YYYY-MM-DD.md` | 그날 나온 로봇 뉴스 |
| `src/.vuepress/home.md` | 메인 페이지에 넣을 카테고리별 최신 뉴스 구획 — `src/README.md`가 불러옵니다 |
| `src/.vuepress/news.ts` | 메뉴에 넣을 날짜 페이지 목록을 읽는 함수 |

- 카테고리 첫 페이지는 따로 없습니다. 메뉴에서 AI·로봇을 누르거나 `/news/ai/`로 들어오면 가장 최근 날짜 페이지로 이동합니다.
- 메인 페이지에는 카테고리별로 가장 최근 날짜의 기사를 최신순으로 5건까지 보여 줍니다. 그날 기사가 5건보다 적으면 있는 만큼만 나옵니다.
  스크립트를 한 번도 실행하지 않아 `src/.vuepress/home.md`가 없으면 메인 페이지에 `File not found`가 표시됩니다.
- 메뉴의 날짜 목록은 빌드(또는 개발 서버 시작) 때 `src/news/<카테고리>/`의 파일을 읽어 만듭니다.
  개발 서버 실행 중에 뉴스를 새로 수집했다면 서버를 다시 시작해야 메뉴에 반영됩니다.
- 실행할 때마다 **어제 00:00 KST부터 현재까지** 기사 중 처음 보는 기사만 `data/news/`에 저장하고, 날짜별 페이지를 다시 만듭니다.
- `data/news/` 저장소는 로컬에만 남기고, `src/news/` 페이지와 `src/.vuepress/home.md`는 **빌드 시점의 어제 00:00부터 현재까지** 기사만 사용합니다. 어제 이전 기사는 저장하지 않습니다.
- 페이지에는 기사 제목, 원문 링크, 출처, 시간만 넣습니다. 기사 본문과 대표 이미지는 가져오지 않습니다.
- 해외 기사 제목은 번역하지 않고 피드의 원문 제목을 그대로 보여 줍니다.
- Google 뉴스 RSS는 `news.google.com` 링크만 주므로, Google의 비공식 내부 API로 원문 주소를 알아내 링크를 바꿉니다
  (한 번 실행에 최신 150건까지, 1초 간격). 막히거나 실패하면 Google 링크를 그대로 쓰고 다음 실행 때 이어서 시도합니다.
- 로컬 스케줄러가 `src/news/`와 `src/.vuepress/home.md`를 커밋해 `main`에 푸시합니다. `pnpm news:update`는 파일만 생성하고 커밋하지 않습니다.
- 일부 출처가 실패해도 나머지로 진행합니다. 한 카테고리 전체가 실패하면 아무 파일도 바꾸지 않습니다.

## 로컬 스케줄러

Windows 작업 스케줄러에 `scripts/run_local_update.ps1`을 등록합니다. 예를 들어 매일 08:00 KST에 실행하려면 PowerShell(필요하면 관리자 권한)에서 아래 명령을 실행합니다.

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Repos\surisurida.github.io\scripts\run_local_update.ps1"'
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"
Register-ScheduledTask -TaskName "Surisurida Update" -Action $action -Trigger $trigger -Description "Update news and market brief" -Force
```

평일만 실행하려면 트리거를 아래처럼 바꿉니다. 매일 실행하면 주말에도 뉴스는 갱신되고 증시 전망은 생략됩니다.

```powershell
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "08:00"
```

작업 스케줄러는 PC의 로컬 시간을 사용합니다. PC 시간대가 `Asia/Seoul`인지 확인하세요. 작업 스케줄러 GUI에서 해당 작업의 **컴퓨터 깨우기**와 **예약 시작 시간을 놓치면 가능한 한 빨리 실행**을 켜 두세요.

- 작업은 `DEEPSEEK_API_KEY` 환경 변수와 Git push 권한이 설정된 사용자 계정으로 실행해야 합니다.
- 기본 등록은 현재 사용자로 되며, 로그온 상태에서 실행됩니다. 로그온하지 않아도 실행하려면 작업 스케줄러에서 **사용자가 로그온하지 않아도 실행**을 설정하고 해당 계정에 Git·DeepSeek 자격 증명이 있어야 합니다.
- PC가 꺼져 있으면 실행되지 않습니다. 절전 상태에서도 실행하려면 위 설정을 켜세요.
- 실행 로그는 `logs/update-YYYYMMDD-HHMMSS.log`에 남습니다. `logs/`는 커밋하지 않습니다.
- 처음에는 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local_update.ps1 -NoPush`로 커밋까지만 시험해 보세요.

## 배포

GitHub Actions는 `main`에 푸시된 소스를 빌드·배포만 합니다. 뉴스 수집과 증시 전망 작성은 로컬 스케줄러가 미리 수행합니다.

1. 로컬 스케줄러가 `pnpm update:local` 실행
2. `uv run scripts/fetch_news.py` — 뉴스 수집
3. `uv run scripts/write_market_brief.py` — 증시 전망 작성
4. `pnpm test`
5. `src/news/`와 `src/.vuepress/home.md`를 커밋하고 `main`에 푸시
6. GitHub Actions: `pnpm install --frozen-lockfile` → `pnpm docs:build` (테스트는 로컬에서만 실행)
7. `src/.vuepress/dist`를 GitHub Pages에 업로드·배포

Actions 탭에서 **Deploy Docs**를 수동 실행해 배포할 수도 있습니다. 처음 한 번은 저장소 **Settings → Pages → Source**를 **GitHub Actions**로 설정해야 합니다.

## TODO — 템플릿 기본값 정리

아직 vuepress-theme-hope 데모 템플릿의 값이 남아 있습니다.

- [ ] `config.ts`: `title`, `description`, `lang`(`ko-KR`)
- [ ] `theme.ts`: `hostname`, `author`, `logo`, `repo`, `footer`
- [ ] `theme.ts`: 데모용 Giscus 댓글 설정 → 본인 저장소로 교체하거나 제거 (데모 값은 테스트 전용)
- [ ] `theme.ts`: 데모용 암호화 페이지 설정(`/demo/encrypt.html`, 비밀번호 1234) 제거
- [ ] `src/demo/`, `src/guide/` 예제 페이지 정리

## 라이선스

MIT
