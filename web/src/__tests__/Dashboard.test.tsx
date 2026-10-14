import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard from "../pages/Dashboard";
import { useApprovalsStats, useEmployeeStats, usePayrolls, usePayrollStats } from "@/services";

vi.mock("@/services", () => ({
  useApprovalsStats: vi.fn(),
  useEmployeeStats: vi.fn(),
  usePayrolls: vi.fn(),
  usePayrollStats: vi.fn(),
}));

const mockedUseApprovalsStats = vi.mocked(useApprovalsStats);
const mockedUseEmployeeStats = vi.mocked(useEmployeeStats);
const mockedUsePayrolls = vi.mocked(usePayrolls);
const mockedUsePayrollStats = vi.mocked(usePayrollStats);

const refetches = {
  employeeStats: vi.fn(),
  payrollStats: vi.fn(),
  approvalsStats: vi.fn(),
  payrolls: vi.fn(),
};

const employeeStats = {
  totalEmployees: 24,
  activeEmployees: 22,
  inactiveEmployees: 1,
  onLeaveEmployees: 1,
  averageSalary: 192500000,
  totalPayroll: 4620000000,
};

const payrollStats = {
  totalPayrolls: 12,
  totalAmount: 48600000000,
  pendingAmount: 4300000000,
  paidAmount: 44300000000,
  averagePerPayroll: 4050000000,
};

const approvalsStats = {
  pendingCount: 1,
  approvedCount: 18,
  rejectedCount: 2,
  averageApprovalTime: 6.4,
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
  mockedUseEmployeeStats.mockReturnValue({
    isLoading: false,
    isError: false,
    error: null,
    data: { success: true, data: employeeStats },
    refetch: refetches.employeeStats,
  } as never);
  mockedUsePayrollStats.mockReturnValue({
    isLoading: false,
    isError: false,
    error: null,
    data: { success: true, data: payrollStats },
    refetch: refetches.payrollStats,
  } as never);
  mockedUseApprovalsStats.mockReturnValue({
    isLoading: false,
    isError: false,
    error: null,
    data: { success: true, data: approvalsStats },
    refetch: refetches.approvalsStats,
  } as never);
  mockedUsePayrolls.mockReturnValue({
    isLoading: false,
    isError: false,
    error: null,
    data: { success: true, data: { items, total: items.length, page: 1, limit: 5, totalPages: items.length ? 1 : 0 } },
    refetch: refetches.payrolls,
  } as never);
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setSuccessfulQueries();
  });

  it("renders API-backed statistics and the recent payroll list", () => {
    render(<Dashboard />);

    expect(screen.getByRole("heading", { name: "داشبورد عملیاتی" })).toBeInTheDocument();
    expect(screen.getByText("کل کارکنان")).toBeInTheDocument();
    expect(screen.getByText("۱۴۰۵-۰۶")).toBeInTheDocument();
    expect(screen.getByText("پرداخت شده")).toBeInTheDocument();
  });

  it("shows API envelope errors and retries all dashboard queries", () => {
    mockedUseEmployeeStats.mockReturnValue({
      isLoading: false,
      isError: false,
      error: null,
      data: {
        success: false,
        error: { code: "UPSTREAM_UNAVAILABLE", message: "سرویس کارکنان موقتاً در دسترس نیست", statusCode: 503 },
      },
      refetch: refetches.employeeStats,
    } as never);

    render(<Dashboard />);
    expect(screen.getByRole("alert")).toHaveTextContent("سرویس کارکنان موقتاً در دسترس نیست");

    fireEvent.click(screen.getByRole("button", { name: "تلاش دوباره" }));
    expect(refetches.employeeStats).toHaveBeenCalledTimes(1);
    expect(refetches.payrollStats).toHaveBeenCalledTimes(1);
    expect(refetches.approvalsStats).toHaveBeenCalledTimes(1);
    expect(refetches.payrolls).toHaveBeenCalledTimes(1);
  });

  it("shows transport errors instead of presenting the dashboard as healthy", () => {
    mockedUsePayrollStats.mockReturnValue({
      isLoading: false,
      isError: true,
      error: new Error("network unavailable"),
      data: undefined,
      refetch: refetches.payrollStats,
    } as never);

    render(<Dashboard />);
    expect(screen.getByRole("alert")).toHaveTextContent("network unavailable");
    expect(screen.queryByText("هیچ دوره حقوقی برای نمایش وجود ندارد")).not.toBeInTheDocument();
  });

  it("shows an empty state only after a successful empty API response", () => {
    setSuccessfulQueries([]);

    render(<Dashboard />);
    expect(screen.getByRole("status")).toHaveTextContent("هیچ دوره حقوقی برای نمایش وجود ندارد.");
  });
});
