import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Topbar from "../components/layout/Topbar";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="current-path">{location.pathname}</output>;
}

function renderTopbar(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Topbar />
      <LocationProbe />
    </MemoryRouter>,
  );
}

describe("Topbar module navigation", () => {
  it("opens the complete mobile module list with an announced expanded state", () => {
    renderTopbar();

    const openButton = screen.getByRole("button", { name: "باز کردن منوی ماژول‌ها" });
    expect(openButton).toHaveAttribute("aria-expanded", "false");
    expect(openButton).toHaveAttribute("aria-controls", "morva-mobile-module-navigation");

    fireEvent.click(openButton);

    expect(screen.getByRole("button", { name: "بستن منوی ماژول‌ها" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("navigation", { name: "منوی ماژول‌ها در موبایل" })).toBeVisible();
    expect(screen.getByRole("link", { name: /اطلاعات پایه/ })).toBeVisible();
    expect(screen.getByRole("link", { name: /درخواست‌های گزارش/ })).toBeVisible();
  });

  it("navigates to a selected module and closes the mobile navigation", () => {
    renderTopbar();

    fireEvent.click(screen.getByRole("button", { name: "باز کردن منوی ماژول‌ها" }));
    fireEvent.click(screen.getByRole("link", { name: /^پرسنل/ }));

    expect(screen.getByTestId("current-path")).toHaveTextContent("/modules/personnel");
    expect(screen.getByRole("button", { name: "باز کردن منوی ماژول‌ها" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("navigation", { name: "منوی ماژول‌ها در موبایل", hidden: true })).not.toBeVisible();
  });

  it("closes an open navigation on Escape and restores focus to its trigger", () => {
    renderTopbar();

    const openButton = screen.getByRole("button", { name: "باز کردن منوی ماژول‌ها" });
    fireEvent.click(openButton);

    const closeButton = screen.getByRole("button", { name: "بستن منوی ماژول‌ها" });
    fireEvent.keyDown(closeButton, { key: "Escape", code: "Escape" });

    const restoredButton = screen.getByRole("button", { name: "باز کردن منوی ماژول‌ها" });
    expect(restoredButton).toHaveAttribute("aria-expanded", "false");
    expect(restoredButton).toHaveFocus();
  });
});
