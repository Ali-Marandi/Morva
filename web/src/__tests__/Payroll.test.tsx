import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Payroll from "../pages/Payroll";
import { usePayrolls, usePayrollStats } from "../services";

vi.mock("../services", () => ({
  usePayrolls: vi.fn(),
  usePayrollStats: vi.fn(),
}));

const mockedUsePayrolls = vi.mocked(usePayrolls);
const mockedUsePayrollStats = vi.mocked(usePayrollStats);

const stats = {
  totalPayrolls: 2,
  totalAmount: 2400000,
  pendingAmount: 300000,
  paidAmount: 2100000,
  averagePerPayroll: 1200000,
};

const payroll = {
  id: "payroll-1405-06",
  period: "۱۴۰۵-۰۶",
  payDate: "2026-09-22",
  status: "paid" as const,
  totalAmount: 1200000,
  employeeCount: 25,
  createdBy: "test-user",
  createdAt: "2026-09-01T08:00:00Z",
  updatedAt: "2026-09-22T08:00:00Z",
};

function setSuccessfulQueries(items = [payroll]) {
  mockedUsePayrollStats.mockReturnValue({
    isLoading: false,
    error: null,
    data: { success: true, data: stats },
    refetch: vi.fn(),
  } as never);
  mockedUsePayrolls.mockReturnValue({
    isLoading: false,
    error: null,
    data: { success: true, data: { items, total: items.length, page: 1, limit: 50, totalPages: 1 } },
    refetch: vi.fn(),
  } as never);
}

describe("Payroll page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders statistics and payroll rows returned by the API hooks", () => {
    setSuccessfulQueries();
    render(<Payroll />);

    expect(screen.getByText("دوره‌های حقوق اخیر")).toBeInTheDocument();
    expect(screen.getByText("۱۴۰۵-۰۶")).toBeInTheDocument();
    expect(screen.getByText("پرداخت شده")).toBeInTheDocument();
    expect(screen.getByText("۲")).toBeInTheDocument();
  });

  it("shows a loading state while API queries are pending", () => {
    mockedUsePayrollStats.mockReturnValue({
      isLoading: true,
      error: null,
      data: undefined,
      refetch: vi.fn(),
    } as never);
    mockedUsePayrolls.mockReturnValue({
      isLoading: true,
      error: null,
      data: undefined,
      refetch: vi.fn(),
    } as never);

    render(<Payroll />);
    expect(screen.getByRole("status")).toHaveTextContent("در حال دریافت اطلاعات حقوق");
  });

  it("shows API failures and retries both queries", () => {
    const statsRefetch = vi.fn();
    const payrollsRefetch = vi.fn();
    mockedUsePayrollStats.mockReturnValue({
      isLoading: false,
      error: new Error("دریافت آمار ناموفق بود"),
      data: undefined,
      refetch: statsRefetch,
    } as never);
    mockedUsePayrolls.mockReturnValue({
      isLoading: false,
      error: null,
      data: { success: true, data: { items: [], total: 0, page: 1, limit: 50, totalPages: 0 } },
      refetch: payrollsRefetch,
    } as never);

    render(<Payroll />);
    expect(screen.getByRole("alert")).toHaveTextContent("دریافت آمار ناموفق بود");
    fireEvent.click(screen.getByRole("button", { name: "تلاش دوباره" }));
    expect(statsRefetch).toHaveBeenCalledTimes(1);
    expect(payrollsRefetch).toHaveBeenCalledTimes(1);
  });

  it("shows an explicit empty state when the API returns no payroll periods", () => {
    setSuccessfulQueries([]);
    render(<Payroll />);
    expect(screen.getByRole("status")).toHaveTextContent("هیچ دوره حقوقی برای نمایش وجود ندارد");
  });
});
