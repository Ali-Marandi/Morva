import { describe, expect, it } from "vitest";
import { findModuleItem, moduleMenus, type ModuleItem } from "../config/moduleNavigation";

function flatten(items: ModuleItem[]): ModuleItem[] {
  return items.flatMap((item) => [item, ...(item.children ? flatten(item.children) : [])]);
}

describe("Module navigation registry", () => {
  const items = flatten(moduleMenus);

  it("assigns a unique route identifier to every module item", () => {
    const ids = items.map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("resolves every route identifier to its own navigation item", () => {
    for (const item of items) {
      expect(findModuleItem(item.id)).toBe(item);
    }
  });
});
