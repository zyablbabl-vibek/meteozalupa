import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InsightsPanel } from "./InsightsPanel";

const data = {
  horizon: "today" as const,
  period_start: "2026-07-31",
  period_end: "2026-07-31",
  selected_date: "2026-07-31",
  disclaimer:
    "Автоматический анализ прогнозных моделей. Не является официальным метеорологическим предупреждением.",
  precipitation: {
    total: 1,
    items: [
      {
        category: "precipitation" as const,
        severity: "attention" as const,
        reason_code: "PRECIP_DAILY_TOTAL",
        title: "Значительная суточная сумма",
        description: "Ожидаются осадки.",
        explanation: "Значение выше продуктового порога 10 мм.",
        period_start: null,
        period_end: null,
        point_id: "x",
        point_name: "Зея",
        models: ["ECMWF IFS", "NOAA GFS"],
        values: {},
      },
    ],
  },
  wind: { total: 0, items: [] },
};

describe("InsightsPanel", () => {
  it("shows disclaimer, empty state and explanation", () => {
    render(<InsightsPanel data={data} />);
    expect(screen.getByText(/не является официальным/i)).toBeInTheDocument();
    expect(
      screen.getByText(/не выделяют заметных особенностей по ветру/i),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("Почему это выделено?"));
    expect(screen.getByText(/продуктового порога 10 мм/i)).toBeVisible();
  });
});
