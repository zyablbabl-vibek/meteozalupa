import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgreementBadge } from "./AgreementBadge";
describe("AgreementBadge", () => {
  it("shows agreement", () => {
    render(<AgreementBadge level="низкое" />);
    expect(screen.getByText("низкое")).toBeInTheDocument();
  });
});
