import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { HorizonControl } from "./HorizonControl";

describe("HorizonControl", () => {
  it("switches between today, 3d and 7d", () => {
    const change = vi.fn();
    render(<HorizonControl value="today" onChange={change} />);
    expect(screen.getByText("Сегодня")).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByText("3 дня"));
    fireEvent.click(screen.getByText("7 дней"));
    expect(change).toHaveBeenNthCalledWith(1, "3d");
    expect(change).toHaveBeenNthCalledWith(2, "7d");
  });
});
