import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Approvals from "../pages/Approvals";
import { useApprovals, useApprovalsStats } from "@/services";

vi.mock("@/services", () => ({
  useApprovals: vi.fn(),
  useApprovalsStats: vi.fn(),
}));

vi.mock("@/services/demo", () => ({ DEMO_MODE: false }));

const mockedUseApprovals = vi.mocked(useApprovals);
const mockedUseApprovalsStats = vi.mocked(useApprovalsStats);
const refetchApprovals = vi.fn();
const refetchStats = vi.fn();

const stats = {
  pendingCount: 1,
  approvedCount: 1,
  rejectedCount: 1,
  averageApprovalTime: 4.2,
};

const approvals = [
  {
    id: "approval-1",
    type: "payroll" as const,
    referenceId: "payroll-1405-06",
    status: "pending" as const,
    requestedBy: "user-1",
    approverEmail: "manager@example.com",
    createdAt: "2026-09-01T08:00:00Z",
    updatedAt: "2026-09-01T08:00:00Z",
    amount: 1200000,
  },
  {
    id: "approval-2",
    type: "leave" as const,
    referenceId: "leave-002",
    status: "approved" as const,
    requestedBy: "user-2",
    approverEmail: "manager@example.com",
    createdAt: "2026-09-02T08:00:00Z",
    updatedAt: "2026-09-02T08:00:00Z",
  },
  {
    id: "approval-3",
    type: "expense" as const,
    referenceId: "expense-003",
    status: "rejected" as const,
    requestedBy: "user-3",
    approverEmail: "manager@example.com",
    createdAt: "2026-09-03T08:00:00Z",
    updatedAt: "2026-09-03T08:00:00Z",
    amount: 30000,
  },
];

function setSuccessfulQueries(items = approvals) {
  mockedUseApprovalsStats.mockReturnValue({
    isLoading: false,
    isError: false,
    error: null,
    data: { success: true, data: stats },
    refetch: refetchStats,
  } as never);
  mockedUseApprovals.mockReturnValue({
    isLoading: false,
    isError: false,
    error: null,
    data: { success: true, data: { items, total: items.length, page: 1, limit: 50, totalPages: items.length ? 1 : 0 } },
    refetch: refetchApprovals,
  } as never);
}

describe("Approvals page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setSuccessfulQueries();
  });

  it("renders API-backed statistics and approval records without fake action buttons", () => {
    render(<Approvals />);

    expect(screen.getByRole("heading", { name: "صف تأییدها" })).toBeInTheDocument();
    expect(screen.getByText("payroll-1405-06")).toBeInTheDocument();
    expect(screen.getByText("حقوق و دستمزد")).toBeInTheDocument();
    expect(screen.getAllByText("در انتظار")).toHaveLength(2);
    expect(screen.getAllByRole("button").some((button) => button.textContent?.trim() === "تأیید")).toBe(false);
    expect(screen.getAllByRole("button").some((button) => button.textContent?.trim() === "رد")).toBe(false);
  });

  it("filters the returned approval records by status", () => {
    render(<Approvals />);

    const pendingFilter = screen.getAllByRole("button").find((button) => button.textContent?.trim() === "در انتظار");
    expect(pendingFilter).toBeDefined();
    fireEvent.click(pendingFilter!);

    expect(screen.getByText("payroll-1405-06")).toBeInTheDocument();
    expect(screen.queryByText("leave-002")).not.toBeInTheDocument();
    expect(screen.queryByText("expense-003")).not.toBeInTheDocument();
  });

  it("shows API envelope errors and retries both queries", () => {
    mockedUseApprovals.mockReturnValue({
      isLoading: false,
      isError: false,
      error: null,
      data: {
        success: false,
        error: { code: "UPSTREAM_UNAVAILABLE", message: "سرویس درخواست‌ها موقتاً در دسترس نیست", statusCode: 503 },
      },
      refetch: refetchApprovals,
    } as never);

    render(<Approvals />);
    expect(screen.getByRole("alert")).toHaveTextContent("سرویس درخواست‌ها موقتاً در دسترس نیست");

    fireEvent.click(screen.getByRole("button", { name: "تلاش دوباره" }));
    expect(refetchApprovals).toHaveBeenCalledTimes(1);
    expect(refetchStats).toHaveBeenCalledTimes(1);
  });

  it("shows loading and successful empty states", () => {
    mockedUseApprovalsStats.mockReturnValue({
      isLoading: true,
      isError: false,
      error: null,
      data: undefined,
      refetch: refetchStats,
    } as never);
    mockedUseApprovals.mockReturnValue({
      isLoading: true,
      isError: false,
      error: null,
      data: undefined,
      refetch: refetchApprovals,
    } as never);

    const { rerender } = render(<Approvals />);
    expect(screen.getByRole("status")).toHaveTextContent("در حال دریافت درخواست‌ها");

    setSuccessfulQueries([]);
    rerender(<Approvals />);
    expect(screen.getByRole("status")).toHaveTextContent("هیچ درخواستی برای نمایش وجود ندارد.");
  });
});
