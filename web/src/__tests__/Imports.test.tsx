import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Imports from "../pages/Imports";
import { importService } from "@/services";

vi.mock("@/services", () => ({
  importService: { getSummary: vi.fn(), upload: vi.fn() },
}));

const mockedGetSummary = vi.mocked(importService.getSummary);
const mockedUpload = vi.mocked(importService.upload);

const summary = {
  categories: { employees: "کارکنان" },
  totals: { employees: 2 },
  sources: [
    {
      sourceKey: "employees.xlsx:Sheet1",
      fileName: "employees.xlsx",
      category: "employees",
      categoryLabel: "کارکنان",
      sheetName: "Sheet1",
      headers: ["نام"],
      importedAt: "invalid-date",
      recordCount: 2,
    },
  ],
};

describe("Imports", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetSummary.mockResolvedValue({ success: true, data: summary } as never);
    mockedUpload.mockResolvedValue({
      success: true,
      data: { message: "فایل با موفقیت وارد شد", imported: {} },
    } as never);
  });

  it("shows a summary request failure in the summary section with an accessible retry", async () => {
    mockedGetSummary.mockRejectedValueOnce(new Error("خلاصه در دسترس نیست"));

    render(<Imports />);

    expect(await screen.findByRole("alert")).toHaveTextContent("خلاصه در دسترس نیست");
    const retry = screen.getByRole("button", { name: "تلاش دوباره" });
    expect(retry).toBeEnabled();

    fireEvent.click(retry);
    expect(await screen.findAllByText("کارکنان")).toHaveLength(2);
    expect(mockedGetSummary).toHaveBeenCalledTimes(2);
  });

  it("names the icon-only summary refresh control for assistive technology", async () => {
    render(<Imports />);

    await screen.findByText("employees.xlsx");
    expect(screen.getByRole("button", { name: "به‌روزرسانی وضعیت واردسازی" })).toBeInTheDocument();
  });

  it("keeps malformed import timestamps visible without crashing the table", async () => {
    render(<Imports />);

    expect(await screen.findByRole("row", { name: /employees\.xlsx/ })).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows upload failures separately from summary failures", async () => {
    mockedUpload.mockRejectedValueOnce(new Error("بارگذاری فایل ناموفق بود"));
    const file = new File(["sample"], "employees.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    render(<Imports />);
    await screen.findByText("employees.xlsx");
    fireEvent.change(screen.getByLabelText(/انتخاب و واردسازی فایل/), { target: { files: [file] } });

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("بارگذاری فایل ناموفق بود"));
    expect(screen.getAllByText("کارکنان")).toHaveLength(2);
  });
});
