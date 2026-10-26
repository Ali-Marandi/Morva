import "@testing-library/jest-dom/vitest";
import React from "react";
import { readFileSync } from "node:fs";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Layout from "../components/layout/Layout";
const styles = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

describe("skip link", () => {
  it("targets the keyboard-focusable main landmark", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<p>Page content</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    const skipLink = screen.getByRole("link", { name: "رفتن به محتوای اصلی" });
    const main = screen.getByRole("main");

    expect(skipLink).toHaveAttribute("href", "#main-content");
    expect(main).toHaveAttribute("id", "main-content");
    expect(main).toHaveAttribute("tabindex", "-1");
  });

  it("preserves a visible focus indicator on the skip-link destination", () => {
    const focusRule = styles.match(/#main-content:focus\s*\{([^}]*)\}/);

    expect(focusRule).not.toBeNull();
    expect(focusRule?.[1]).toMatch(/outline:\s*3px solid #1d4ed8;/);
    expect(focusRule?.[1]).toMatch(/outline-offset:\s*-3px;/);
    expect(focusRule?.[1]).not.toMatch(/outline:\s*none/);
  });
});
