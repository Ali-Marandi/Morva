import "@testing-library/jest-dom/vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Settings from "../pages/Settings";

describe("Settings page", () => {
  it("explains that settings are not persisted and does not present fake controls or status", () => {
    render(<Settings />);

    expect(screen.getByRole("status")).toHaveTextContent("ذخیره تنظیمات هنوز در دسترس نیست");
    expect(screen.getByText(/چیزی تغییر یا ذخیره نمی‌شود/)).toBeInTheDocument();
    expect(screen.getByText("تأیید دومرحله‌ای")).toBeInTheDocument();
    expect(screen.getByText("پشتیبان‌گیری خودکار")).toBeInTheDocument();
    expect(screen.getAllByText("در دسترس نیست")).toHaveLength(4);
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText("۹۸/۱۰۰")).not.toBeInTheDocument();
    expect(screen.queryByText("۱۰۰%")).not.toBeInTheDocument();
  });
});
