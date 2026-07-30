import { describe, expect, it } from "vitest";
import { number, temperature } from "./format";
describe("formatters", () => {
  it("formats values and missing data", () => {
    expect(number(null)).toBe("—");
    expect(temperature(3.14)).toBe("+3.1°");
  });
});
