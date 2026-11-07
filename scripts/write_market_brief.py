# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""증시 전망 페이지를 Claude Code로 작성해 src/news/market/YYYY-MM-DD.md로 만든다.

실행: uv run scripts/write_market_brief.py   (배포 워크플로가 뉴스 수집 다음에 실행한다)

뉴스 페이지처럼 커밋하지 않는 일회성 파일이다. 작성에 비용이 들어 한국 평일에 하루 한 번만 만들고,
그 사이의 배포는 워크플로가 캐시에서 되살린 페이지를 그대로 쓴다.

1. 오늘 페이지가 있거나, 주말이거나, 뉴욕 마감 자료가 다 나오기 전이면 아무것도 하지 않는다.
   환경 변수 MARKET_BRIEF_FORCE가 Y이면 이 조건들을 건너뛰고 새로 쓴다.
2. Claude Code가 scripts/market_brief/write.md대로 웹을 조사해 새 페이지 하나를 쓴다.
3. 새 페이지 외의 변경이 없는지 확인하고 pnpm test를 실행한다.
4. 도구 없는 별도 실행이 scripts/market_brief/review.md 기준으로 법률 검토를 한다.
5. 모두 통과하면 이전 페이지를 지우고 새 페이지만 남긴다.

종료 코드:
- 0: 배포를 계속한다. 시크릿이 없거나 API 오류·자료 부족으로 작성하지 못한 경우도 여기에 해당하며,
     새 페이지는 지우고 직전 페이지로(없으면 증시 전망 없이) 빌드한다.
- 1: 위반을 찾았다. 새 페이지를 지우고 배포를 중단한다.
"""

import json
import os
import shutil
import subprocess
import sys
import time as clock
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# 한국은 서머타임이 없으므로 고정 오프셋을 쓴다 (Windows에서도 tzdata 없이 동작).
KST = timezone(timedelta(hours=9), "KST")

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "src" / "news" / "market"
PROMPT_DIR = ROOT / "scripts" / "market_brief"
EXAMPLE_PAGE = "scripts/market_brief/2026-11-06.md"  # 형식 본보기이자 tests/market.test.ts의 검사 대상

CLAUDE_CODE_PACKAGE = "@anthropic-ai/claude-code@2.1.318"
MODEL = "claude-opus-5-5"
SECRETS = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
FORCE_VARIABLE = "MARKET_BRIEF_FORCE"  # 저장소 Actions 변수에서 받는다.

# 뉴욕 종가, WTI 정산가, 필라델피아 반도체 지수 최종 표기가 모두 나온 뒤의 한국 시각이다.
READY_AT = time(7, 30)
# 작성 실패가 이어져도 지난 전망이 계속 걸려 있지 않도록, 이보다 오래된 페이지는 내린다.
MAX_PAGE_AGE = timedelta(days=4)
WRITE_TIMEOUT = 40 * 60  # 작성 실행을 기다리는 최대 시간(초)
REVIEW_TIMEOUT = 10 * 60  # 법률 검토 실행을 기다리는 최대 시간(초)
WRITE_BUDGET_USD = "10"  # 작성 실행의 비용 상한
REVIEW_BUDGET_USD = "2"  # 법률 검토 실행의 비용 상한

# Ubuntu 24.04부터 있는 사용자 네임스페이스 제한 설정과, Claude Code가 명령을 격리할 때와 같은 bubblewrap 옵션이다.
USERNS_RESTRICTION = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns")
BWRAP_TRIAL = [
    "bwrap", "--new-session", "--die-with-parent", "--unshare-user", "--unshare-pid",
    "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "/bin/true",
]

# Yahoo는 약관이 자동 수집을 금지하고 Finviz도 제한한다고 알려져 있어 직접 가져오지 않는다.
BLOCKED_FETCHES = "WebFetch(domain:*.yahoo.com),WebFetch(domain:finviz.com),WebFetch(domain:*.finviz.com)"
WRITE_SCHEMA = {
    "type": "object",
    "properties": {"status": {"type": "string", "enum": ["created", "halted"]}, "reason": {"type": "string"}},
    "required": ["status", "reason"],
}
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "violation"]},
        "findings": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "findings", "notes"],
}

APPROVED, NOT_WRITTEN, VIOLATION = "approved", "not_written", "violation"


def warn(message: str) -> None:
    print(f"::warning::{message}")


def error(message: str) -> None:
    print(f"::error::{message}")


def summarize(line: str) -> None:
    """Actions 실행 요약에 한 줄을 남긴다."""
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as file:
            file.write(f"{line}\n")


def set_output(line: str) -> None:
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf-8") as file:
            file.write(f"{line}\n")


def one_line(text: object) -> str:
    """Claude가 쓴 글을 로그에 안전하게 남긴다. 한 줄로 만들어 워크플로 명령으로 해석되지 않게 한다."""
    return json.dumps(text, ensure_ascii=False)


def tail(text: str | None, limit: int = 1500) -> str:
    """명령 출력의 끝부분을 로그에 남길 형태로 돌려준다. 실패 이유는 보통 마지막에 있다."""
    return one_line((text or "").strip()[-limit:])


def run_setup(name: str, command: list[str], timeout: int = 300) -> subprocess.CompletedProcess | None:
    """러너 준비 명령을 시크릿 없이 실행한다. 실패하면 이유를 경고로 남기고 None을 돌려준다."""
    env = {key: value for key, value in os.environ.items() if key not in SECRETS}
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as problem:
        warn(f"{name} 실패: {type(problem).__name__}: {one_line(str(problem))}")
        return None
    if completed.returncode != 0:
        warn(f"{name} 실패 (종료 코드 {completed.returncode}): {tail(completed.stderr or completed.stdout)}")
        return None
    return completed


def find_claude() -> str | None:
    """claude 명령의 경로를 돌려준다. 작성하지 않는 배포를 느리게 하지 않도록 필요할 때만 러너에 설치한다."""
    if not shutil.which("claude") and "GITHUB_ACTIONS" in os.environ:
        run_setup("Claude Code 설치", ["npm", "install", "-g", CLAUDE_CODE_PACKAGE])
    claude = shutil.which("claude")
    if claude and (version := run_setup("claude --version", [claude, "--version"], timeout=60)):
        print(f"Claude Code: {claude} {tail(version.stdout)}")
    return claude


def prepare_isolation() -> bool:
    """러너에서 작성 실행의 명령 격리를 준비한다. 격리가 동작하면 True를 돌려준다.

    Linux의 Claude Code는 CLAUDE_CODE_SUBPROCESS_ENV_SCRUB을 켜면 bubblewrap을 요구하는데, 러너에는 없고
    Ubuntu의 AppArmor도 이를 막는다. 공식 claude-code-action과 같은 방법으로 풀어 준다.
    """
    if "GITHUB_ACTIONS" not in os.environ or sys.platform != "linux":
        return True
    if not shutil.which("bwrap"):
        for _ in range(3):  # 패키지 저장소가 잠시 응답하지 않을 때가 있어 다시 시도한다.
            if run_setup("apt-get update", ["sudo", "-n", "apt-get", "update", "-qq"]) and run_setup(
                "bubblewrap 설치",
                ["sudo", "-n", "apt-get", "install", "-y", "--no-install-recommends", "bubblewrap", "socat"],
            ):
                break
            clock.sleep(5)
    if USERNS_RESTRICTION.exists():
        run_setup(
            "사용자 네임스페이스 제한 해제",
            ["sudo", "-n", "sysctl", "-w", "kernel.apparmor_restrict_unprivileged_userns=0"],
        )
    # 격리가 막혀 있으면 조사 비용을 다 쓴 뒤에야 pnpm test에서 실패하므로, 쓰기 전에 시험해 본다.
    return run_setup("bubblewrap 동작 확인", BWRAP_TRIAL, timeout=60) is not None


def run_claude(claude: str, step: str, prompt: str, options: list[str], timeout: int, env: dict[str, str]) -> dict:
    """Claude Code를 한 번 실행해 구조화된 결과를 돌려준다. 결과를 얻지 못하면 빈 dict를 돌려준다."""
    command = [claude, "-p", "--model", MODEL, "--effort", "high", "--output-format", "json", *options]
    try:
        completed = subprocess.run(
            command, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=ROOT, env=env, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        warn(f"{step}: Claude Code가 {timeout}초 안에 끝나지 않았습니다.")
        return {}
    except OSError as problem:
        warn(f"{step}: Claude Code를 실행하지 못했습니다: {one_line(str(problem))}")
        return {}
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        # 옵션 오류나 시작 실패 때는 JSON 없이 stderr에만 이유를 남기고 끝난다.
        warn(f"{step}: Claude Code가 JSON 결과를 내지 않았습니다 (종료 코드 {completed.returncode}). stderr: {tail(completed.stderr)}")
        print(f"{step} 표준 출력: {tail(completed.stdout)}")
        return {}

    shown = ("subtype", "is_error", "num_turns", "total_cost_usd", "structured_output")
    print(f"{step} 결과: {one_line({key: result.get(key) for key in shown})}")
    if result.get("is_error"):
        warn(f"{step} 오류: {one_line(result.get('result'))}")
    summarize(f"{step}: 추정 비용 ${result.get('total_cost_usd', '?')}, 턴 {result.get('num_turns', '?')}")
    return result.get("structured_output") or {}


def git_status() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT, check=True,
    ).stdout


def run_tests(env: dict[str, str]) -> bool:
    pnpm = shutil.which("pnpm") or "pnpm"
    completed = subprocess.run(
        [pnpm, "test"], capture_output=True, text=True, encoding="utf-8", cwd=ROOT, env=env, check=False
    )
    if completed.returncode != 0:
        print(completed.stdout[-4000:])
    return completed.returncode == 0


def create_page(claude: str, page: Path, now: datetime) -> str:
    """새 페이지를 쓰고 검사한다. APPROVED가 아니면 호출한 쪽이 페이지를 지운다."""
    relative = page.relative_to(ROOT).as_posix()
    base_env = {key: value for key, value in os.environ.items() if value or key not in SECRETS}
    base_env |= {"DISABLE_AUTOUPDATER": "1", "TZ": "Asia/Seoul"}
    test_env = {key: value for key, value in base_env.items() if key not in SECRETS}

    before = git_status()

    # 수정은 새 페이지 하나만 허용하고, 실행은 pnpm test와 작업 폴더 안의 읽기 전용 명령만 된다.
    # 나머지 승인이 필요한 호출은 모두 거부되며, 작업 폴더 밖의 파일은 읽을 수 없다.
    prompt = (PROMPT_DIR / "write.md").read_text(encoding="utf-8") + (
        f"\n## 이번 실행\n\n- 현재 시각: {now:%Y-%m-%d %H:%M} KST\n- 새 페이지: {relative}\n- 본보기 페이지: {EXAMPLE_PAGE}\n"
    )
    written = run_claude(
        claude,
        "작성",
        prompt,
        [
            "--max-budget-usd", WRITE_BUDGET_USD,
            "--permission-prompts", "none",
            "--tools", "Read,Write,Edit,WebSearch,WebFetch,Bash",
            "--allowedTools", f"WebSearch,WebFetch,Edit({relative}),Bash(pnpm test)",
            "--disallowedTools", BLOCKED_FETCHES,
            "--json-schema", json.dumps(WRITE_SCHEMA),
        ],
        WRITE_TIMEOUT,
        base_env | {"CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1"},
    )
    if written.get("status") != "created" or not page.exists():
        warn(f"증시 전망을 작성하지 못해 직전 페이지로 빌드합니다: {one_line(written.get('reason', '결과 없음'))}")
        return NOT_WRITTEN

    if git_status() != before:
        error("새 페이지 외의 파일이 바뀌어 배포를 중단합니다.")
        print(git_status())
        return VIOLATION

    if not run_tests(test_env):
        error("새 페이지가 검사를 통과하지 못해 배포를 중단합니다.")
        return VIOLATION

    # 작성과 분리해 도구 없이 페이지 내용만 보고 판정한다.
    prompt = (
        (PROMPT_DIR / "review.md").read_text(encoding="utf-8")
        + f"\n<page>\n{page.read_text(encoding='utf-8')}</page>\n"
    )
    reviewed = run_claude(
        claude,
        "법률 검토",
        prompt,
        ["--max-budget-usd", REVIEW_BUDGET_USD, "--tools", "", "--json-schema", json.dumps(REVIEW_SCHEMA)],
        REVIEW_TIMEOUT,
        base_env,
    )
    verdict = reviewed.get("verdict")
    summarize(f"법률 검토: {verdict or '결과 없음'}")
    for finding in reviewed.get("findings", []):
        summarize(f"- 위반: {finding}")
    for note in reviewed.get("notes", []):
        summarize(f"- 참고: {note}")

    if verdict == "pass":
        return APPROVED
    if verdict == "violation":
        error("법률 검토에서 위반을 찾아 배포를 중단합니다.")
        return VIOLATION
    warn("법률 검토 결과를 얻지 못해 새 페이지를 게시하지 않고 직전 페이지로 빌드합니다.")
    return NOT_WRITTEN


def page_files() -> list[Path]:
    return sorted(PAGES_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"))


def main(now: datetime | None = None) -> int:
    now = now or datetime.now(KST)
    today = now.date()
    force = os.environ.get(FORCE_VARIABLE, "").strip().upper() == "Y"

    for path in page_files():
        if today - date.fromisoformat(path.stem) > MAX_PAGE_AGE:
            print(f"오래된 증시 전망을 내립니다: {path.name}")
            path.unlink()

    page = PAGES_DIR / f"{today}.md"
    if not force:
        if page.exists():
            print(f"{page.name}이 이미 있어 새로 작성하지 않습니다.")
            return 0
        if now.weekday() >= 5:
            print("주말에는 작성하지 않고 직전 페이지를 그대로 씁니다.")
            return 0
        if now.time() < READY_AT:
            print(f"뉴욕 마감 자료가 다 나오는 {READY_AT:%H:%M} 전이라 직전 페이지를 그대로 씁니다.")
            return 0
    if not any(os.environ.get(name) for name in SECRETS):
        warn(f"시크릿 {' 또는 '.join(SECRETS)}가 없어 증시 전망을 작성하지 않습니다.")
        return 0
    claude = find_claude()
    if not claude:
        warn("claude 명령을 찾지 못해 증시 전망을 작성하지 않습니다.")
        return 0
    if not prepare_isolation():
        warn("명령 격리를 준비하지 못해 증시 전망을 작성하지 않습니다.")
        return 0

    if force:
        warn(f"{FORCE_VARIABLE}가 Y라서 조건과 관계없이 새로 씁니다. 그대로 두면 배포할 때마다 비용이 드니 N으로 되돌리세요.")

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    # 강제 실행이면 오늘 페이지가 이미 있을 수 있다. 빈 자리에서 새로 쓰게 하고, 통과하지 못하면 되돌린다.
    previous = page.read_bytes() if page.exists() else None
    page.unlink(missing_ok=True)
    outcome = create_page(claude, page, now)
    if outcome != APPROVED:
        page.unlink(missing_ok=True)
        if previous is not None:
            page.write_bytes(previous)
        return 1 if outcome == VIOLATION else 0

    for path in page_files():
        if path != page:
            path.unlink()
    set_output("created=true")
    print(f"완료: {page.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
