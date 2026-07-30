import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SectionControl } from "./SectionControl";

describe("SectionControl", () => {
  it("switches temperature, precipitation and wind", () => {
    const change = vi.fn();
    render(<SectionControl value="temperature" onChange={change} />);
    fireEvent.click(screen.getByText("Осадки"));
    fireEvent.click(screen.getByText("Ветер"));
    expect(change).toHaveBeenNthCalledWith(1, "precipitation");
    expect(change).toHaveBeenNthCalledWith(2, "wind");
  });
});
