import "@testing-library/jest-dom/vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Objections from "../pages/Objections";
import { selfService } from "@/services/self-service";

vi.mock("@/services/self-service", () => ({
  selfService: {
    getCases: vi.fn(),
    createCase: vi.fn(),
  },
}));

const mockedGetCases = vi.mocked(selfService.getCases);
const mockedCreateCase = vi.mocked(selfService.createCase);

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <Objections />
    </QueryClientProvider>,
  );
}

describe("Objections page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCases.mockResolvedValue({ success: true, data: [] } as never);
  });

  it("shows an empty state only after a successful response", async () => {
    renderPage();
    expect(await screen.findByText("پرونده‌ای ثبت نشده است.")).toHaveAttribute("role", "status");
  });

  it("shows API envelope failures with a retry instead of a false empty state", async () => {
    mockedGetCases.mockResolvedValueOnce({
      success: false,
      error: { code: "CASES_UNAVAILABLE", message: "فهرست پرونده‌ها در دسترس نیست" },
    } as never);
    mockedGetCases.mockResolvedValueOnce({ success: true, data: [] } as never);

    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("فهرست پرونده‌ها در دسترس نیست");
    expect(screen.queryByText("پرونده‌ای ثبت نشده است.")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "تلاش دوباره" }));
    expect(await screen.findByText("پرونده‌ای ثبت نشده است.")).toBeInTheDocument();
    expect(mockedGetCases).toHaveBeenCalledTimes(2);
  });

  it("reports mutation envelope failures and keeps the entered request", async () => {
    mockedCreateCase.mockResolvedValue({
      success: false,
      error: { code: "CASE_REJECTED", message: "ثبت درخواست رد شد" },
    } as never);

    renderPage();
    fireEvent.change(screen.getByLabelText("عنوان"), { target: { value: "درخواست بررسی" } });
    fireEvent.change(screen.getByLabelText("شرح"), { target: { value: "لطفاً این مورد را بررسی کنید." } });
    fireEvent.click(screen.getByRole("button", { name: "ثبت" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("ثبت درخواست رد شد");
    expect(screen.getByLabelText("عنوان")).toHaveValue("درخواست بررسی");
    expect(mockedCreateCase).toHaveBeenCalledTimes(1);
  });

  it("announces a successful request submission", async () => {
    mockedCreateCase.mockResolvedValue({ success: true, data: { id: "case-1" } } as never);

    renderPage();
    fireEvent.change(screen.getByLabelText("عنوان"), { target: { value: "درخواست بررسی" } });
    fireEvent.change(screen.getByLabelText("شرح"), { target: { value: "لطفاً این مورد را بررسی کنید." } });
    fireEvent.click(screen.getByRole("button", { name: "ثبت" }));

    expect(await screen.findByText("درخواست با موفقیت ثبت شد.")).toHaveAttribute("role", "status");
    expect(screen.getByLabelText("عنوان")).toHaveValue("");
  });
});
