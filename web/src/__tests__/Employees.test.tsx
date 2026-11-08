import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Employees from "../pages/Employees";
import { useEmployeeStats, useEmployees } from "@/services";

vi.mock("@/services", () => ({
  useEmployeeStats: vi.fn(),
  useEmployees: vi.fn(),
}));

const mockedUseEmployeeStats = vi.mocked(useEmployeeStats);
const mockedUseEmployees = vi.mocked(useEmployees);
const refetchStats = vi.fn();
const refetchEmployees = vi.fn();

const stats = {
  totalEmployees: 1,
  activeEmployees: 1,
  inactiveEmployees: 0,
  onLeaveEmployees: 0,
  averageSalary: 100,
  totalPayroll: 100,
};

const employee = {
  id: "employee-1",
  name: "کارمند نمونه",
  email: "employee@example.test",
  phone: "000",
  department: "آموزش",
  position: "کارشناس",
  salary: 100,
  baseSalary: 100,
  benefits: 0,
  status: "active" as const,
  joinDate: "2026-01-01",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

function setSuccessfulQueries(items = [employee]) {
  mockedUseEmployeeStats.mockReturnValue({
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    data: { success: true, data: stats },
    refetch: refetchStats,
  } as never);
  mockedUseEmployees.mockReturnValue({
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    data: { success: true, data: { items, total: items.length, page: 1, limit: 50, totalPages: items.length ? 1 : 0 } },
    refetch: refetchEmployees,
  } as never);
}

describe("Employees", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setSuccessfulQueries();
  });

  it("renders employee rows and accessible table headers from the API", () => {
    render(<Employees />);

    expect(screen.getByRole("heading", { name: "مدیریت کارکنان" })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /کارمند نمونه/ })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "نام" })).toBeInTheDocument();
  });

  it("shows loading feedback while employee data is pending", () => {
    mockedUseEmployees.mockReturnValue({
      isLoading: true,
      isFetching: true,
      isError: false,
      error: null,
      data: undefined,
      refetch: refetchEmployees,
    } as never);

    render(<Employees />);
    expect(screen.getByRole("status")).toHaveTextContent("در حال دریافت اطلاعات کارکنان");
  });

  it("reports an API envelope error instead of showing a false empty state", () => {
    mockedUseEmployees.mockReturnValue({
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      data: { success: false, error: { code: "EMPLOYEE_LIST_UNAVAILABLE", message: "فهرست کارکنان در دسترس نیست" } },
      refetch: refetchEmployees,
    } as never);

    render(<Employees />);
    expect(screen.getByRole("alert")).toHaveTextContent("فهرست کارکنان در دسترس نیست");
    expect(screen.queryByText("هیچ رکوردی برای نمایش وجود ندارد.")).not.toBeInTheDocument();
  });

  it("shows transport errors and retries both employee queries", () => {
    mockedUseEmployeeStats.mockReturnValue({
      isLoading: false,
      isFetching: false,
      isError: true,
      error: new Error("خلاصه کارکنان در دسترس نیست"),
      data: undefined,
      refetch: refetchStats,
    } as never);

    render(<Employees />);
    expect(screen.getByRole("alert")).toHaveTextContent("خلاصه کارکنان در دسترس نیست");

    fireEvent.click(screen.getByRole("button", { name: "تلاش دوباره" }));
    expect(refetchStats).toHaveBeenCalledTimes(1);
    expect(refetchEmployees).toHaveBeenCalledTimes(1);
  });

  it("shows an empty state only after a successful empty list response", () => {
    setSuccessfulQueries([]);

    render(<Employees />);
    expect(screen.getByRole("status")).toHaveTextContent("هیچ رکوردی برای نمایش وجود ندارد.");
  });
});
