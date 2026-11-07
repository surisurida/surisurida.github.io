/**
 * "중국어 로케일 삭제, 한국어를 유일한 로케일로 사용" 변경 사항에 대한 테스트.
 *
 * 실행 방법: pnpm test   (node --test, Node의 기본 TypeScript 지원 사용)
 */
import assert from "node:assert/strict";
import { existsSync, readdirSync, statSync } from "node:fs";
import { registerHooks } from "node:module";
import { join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

// VuePress 소스는 같은 폴더의 TS 파일을 ".js" 확장자로 import합니다. (번들러 방식).
// Node가 직접 불러올 수 있도록 이를 ".ts" 파일로 연결합니다.
// theme.ts의 hopeTheme()은 실행 중인 VuePress 앱이 있어야 하므로, config.ts에는
// 빈 테마를 대신 넣습니다. 이 테스트는 사이트 설정만 검사합니다.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "./theme.js" && context.parentURL?.endsWith("/config.ts")) {
      return { url: "data:text/javascript,export default {}", shortCircuit: true };
    }
    // 뉴스 페이지는 스크립트가 생성하는 파일이라 저장소에 없으므로, 폴더를 읽지 않도록 빈 목록으로 대체합니다.
    if (specifier === "../news.js") {
      return { url: "data:text/javascript,export const newsDates = () => []", shortCircuit: true };
    }
    // 증시 전망 페이지도 배포 때 만들어지므로, 메뉴 구성을 항상 검사할 수 있게 페이지가 하나 있는 것으로 대체합니다.
    if (specifier === "../market.js") {
      return { url: 'data:text/javascript,export const marketDates = () => ["2026-11-06"]', shortCircuit: true };
    }
    try {
      return nextResolve(specifier, context);
    } catch (error) {
      if (specifier.startsWith(".") && specifier.endsWith(".js")) {
        return nextResolve(specifier.replace(/\.js$/, ".ts"), context);
      }
      throw error;
    }
  },
});

const SRC = fileURLToPath(new URL("../src/", import.meta.url));

const { default: config } = await import("../src/.vuepress/config.ts");
const navbarIndex = await import("../src/.vuepress/navbar/index.ts");
const sidebarIndex = await import("../src/.vuepress/sidebar/index.ts");
const { koNavbar } = navbarIndex;
const { koSidebar } = sidebarIndex;

type Item = string | { link?: string; prefix?: string; children?: Item[] | string };

const isExternal = (link: string) => /^(https?:)?\/\//.test(link) || link.startsWith("#");

/** VuePress 경로("/", "/demo/", "/portfolio")를 해당 마크다운 파일 경로로 바꿉니다. */
const routeToFile = (route: string): string => {
  const rel = route.replace(/^\//, "").replace(/\.html$/, "");
  return rel === "" || rel.endsWith("/") ? join(SRC, rel, "README.md") : join(SRC, `${rel}.md`);
};

/** 상단 메뉴/사이드바 항목 트리에서 참조하는 모든 내부 경로를 수집합니다. */
const collectRoutes = (items: Item[], base: string, out: string[] = []): string[] => {
  for (const item of items) {
    if (typeof item === "string") {
      if (!isExternal(item)) out.push(item.startsWith("/") ? item : base + item);
      continue;
    }
    const prefix = item.prefix ? (item.prefix.startsWith("/") ? item.prefix : base + item.prefix) : base;
    if (item.link && !isExternal(item.link)) {
      out.push(item.link.startsWith("/") ? item.link : base + item.link);
    }
    if (Array.isArray(item.children)) collectRoutes(item.children, prefix, out);
    // children: "structure"는 폴더 구조로 자동 생성되므로, 해당 폴더가 있어야 한다.
    if (item.children === "structure") out.push(prefix);
  }
  return out;
};

/** 링크 검사 대상 경로를 돌려줍니다. 생성 파일에 의존하는 뉴스 경로는 제외합니다. */
const checkedRoutes = (items: Item[], base: string): string[] =>
  collectRoutes(items, base).filter((route) => !route.startsWith("/news/"));

const listMarkdown = (dir: string): string[] =>
  readdirSync(dir).flatMap((name) => {
    if (name === ".vuepress") return [];
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return listMarkdown(path);
    return name.endsWith(".md") ? [path] : [];
  });

describe("상단 메뉴와 사이드바", () => {
  it("상단 메뉴에는 증시 전망, AI 뉴스, 로봇 뉴스가 묶이지 않고 바로 나옴", () => {
    const items = (koNavbar as { text: string; children?: unknown }[]).slice(0, 3);
    assert.deepEqual(
      items.map((item) => item.text),
      ["증시 전망", "AI 뉴스", "로봇 뉴스"],
    );
    for (const item of items) {
      assert.equal(item.children, undefined, `상단 메뉴의 ${item.text}에 하위 메뉴가 없어야 합니다`);
    }
  });

  it("사이드바에서는 증시 전망, AI, 로봇이 뉴스 카테고리 아래에 있음", () => {
    const items = (koSidebar as Record<string, unknown>)["/"] as { text?: string; children?: { text: string }[] }[];
    const news = items.find((item) => item.text === "뉴스");
    assert.deepEqual(
      news?.children?.slice(0, 3).map((child) => child.text),
      ["증시 전망", "AI", "로봇"],
    );
  });

  it("상단 메뉴 링크가 실제 페이지에 연결 확인", () => {
    for (const route of checkedRoutes(koNavbar as Item[], "/")) {
      assert.ok(existsSync(routeToFile(route)), `상단 메뉴 경로 ${route}에 해당하는 페이지가 없습니다`);
    }
  });

  it("사이드바 링크가 실제 페이지에 연결 확인", () => {
    for (const [base, items] of Object.entries(koSidebar)) {
      for (const route of checkedRoutes(items as Item[], base)) {
        assert.ok(existsSync(routeToFile(route)), `사이드바 경로 ${route}에 해당하는 페이지가 없습니다`);
      }
    }
  });
});
