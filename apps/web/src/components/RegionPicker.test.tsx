import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Region } from "../types/weather";
import { RegionPicker } from "./RegionPicker";

const region = (id: string, name: string): Region => ({
  id,
  name,
  short_name: name,
  name_prepositional: name,
  name_genitive: name,
  federal_district: "Дальневосточный федеральный округ",
  primary_timezone: "Asia/Yakutsk",
  has_multiple_timezones: false,
  default_point_id: `${id}-center`,
  map_center_latitude: 50,
  map_center_longitude: 130,
  map_zoom: 5,
  data_status: "partially_verified",
  point_count: 20,
  geojson_available: false,
});

describe("RegionPicker", () => {
  it("shows all 11 regions and reports selection", () => {
    const onChange = vi.fn();
    const regions = [
      "Амурская область",
      "Еврейская автономная область",
      "Забайкальский край",
      "Камчатский край",
      "Магаданская область",
      "Приморский край",
      "Республика Бурятия",
      "Республика Саха (Якутия)",
      "Сахалинская область",
      "Хабаровский край",
      "Чукотский автономный округ",
    ].map((name, index) => region(`region-${index}`, name));
    render(
      <RegionPicker regions={regions} value="region-0" onChange={onChange} />,
    );
    expect(screen.getAllByRole("option")).toHaveLength(11);
    expect(
      screen.getAllByRole("option").map((option) => option.textContent),
    ).toEqual(regions.map((item) => item.name));
    fireEvent.change(screen.getByLabelText("Регион Дальнего Востока"), {
      target: { value: "region-5" },
    });
    expect(onChange).toHaveBeenCalledWith("region-5");
  });
});
