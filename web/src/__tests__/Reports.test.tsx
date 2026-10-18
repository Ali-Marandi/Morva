import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Reports from "../pages/Reports";
import { useReports } from "@/services";

vi.mock("@/services", () => ({ useReports: vi.fn() }));

const mockedUseReports = vi.mocked(useReports);
const refetch = vi.fn();

const report = {
  id: "report-1",
  name: "گزارش حقوق مهر",
  type: "payroll" as const,
  period: "۱۴۰۵-۰۷",
  status: "ready" as const,
  format: "pdf" as const,
  createdBy: "test-user",
  createdAt: "2026-10-10T08:00:00Z",
};

describe("Reports", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseReports.mockReturnValue({
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      data: { success: true, data: { items: [report], total: 1, page: 1, limit: 20, totalPages: 1 } },
      refetch,
    } as never);
  });

  it("renders the API report list and does not offer an inert download button", () => {
    render(<Reports />);

    expect(screen.getByRole("heading", { name: "گزارش‌ها" })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /گزارش حقوق مهر/ })).toBeInTheDocument();
    expect(screen.getByText("آماده")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /دانلود/ })).not.toBeInTheDocument();
    expect(screen.getByText(/تولید و دریافت فایل از این رابط فعال نیست/)).toBeInTheDocument();
  });

  it("shows loading feedback while the report request is pending", () => {
    mockedUseReports.mockReturnValue({
      isLoading: true,
      isFetching: true,
      isError: false,
      error: null,
      data: undefined,
      refetch,
    } as never);

    render(<Reports />);
    expect(screen.getByRole("status")).toHaveTextContent("در حال دریافت فهرست گزارش‌ها");
  });

  it("shows transport failures and retries the report query", () => {
    mockedUseReports.mockReturnValue({
      isLoading: false,
      isFetching: false,
      isError: true,
      error: new Error("سرویس گزارش در دسترس نیست"),
      data: undefined,
      refetch,
    } as never);

    render(<Reports />);
    expect(screen.getByRole("alert")).toHaveTextContent("سرویس گزارش در دسترس نیست");

    fireEvent.click(screen.getByRole("button", { name: "تلاش دوباره" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("shows an API envelope error instead of reporting an empty successful list", () => {
    mockedUseReports.mockReturnValue({
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      data: { success: false, error: { code: "REPORTS_UNAVAILABLE", message: "فهرست گزارش‌ها در دسترس نیست" } },
      refetch,
    } as never);

    render(<Reports />);
    expect(screen.getByRole("alert")).toHaveTextContent("فهرست گزارش‌ها در دسترس نیست");
    expect(screen.queryByText("گزارشی برای نمایش ثبت نشده است.")).not.toBeInTheDocument();
  });

  it("shows an empty state only after a successful empty response", () => {
    mockedUseReports.mockReturnValue({
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      data: { success: true, data: { items: [], total: 0, page: 1, limit: 20, totalPages: 0 } },
      refetch,
    } as never);

    render(<Reports />);
    expect(screen.getByRole("status")).toHaveTextContent("گزارشی برای نمایش ثبت نشده است.");
  });
});
