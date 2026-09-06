import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Region } from "../types/weather";
import { RegionPicker } from "./RegionPicker";

const region = (id: string, name: string, federalDistrict: string): Region => ({
  id,
  name,
  short_name: name,
  name_prepositional: name,
  name_genitive: name,
  federal_district: federalDistrict,
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
  it("groups all 21 regions by federal district and reports selection", () => {
    const onChange = vi.fn();
    const farEast = [
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
    ].map((name, index) =>
      region(`far-east-${index}`, name, "Дальневосточный федеральный округ"),
    );
    const siberia = [
      "Алтайский край",
      "Иркутская область",
      "Кемеровская область — Кузбасс",
      "Красноярский край",
      "Новосибирская область",
      "Омская область",
      "Республика Алтай",
      "Республика Тыва",
      "Республика Хакасия",
      "Томская область",
    ].map((name, index) =>
      region(`siberia-${index}`, name, "Сибирский федеральный округ"),
    );
    const regions = [...farEast, ...siberia];
    render(
      <RegionPicker regions={regions} value="far-east-0" onChange={onChange} />,
    );
    expect(screen.getAllByRole("option")).toHaveLength(21);
    expect(screen.getByRole("group", { name: /Дальневосточный/ })).toBeTruthy();
    expect(screen.getByRole("group", { name: /Сибирский/ })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Регион России"), {
      target: { value: "siberia-3" },
    });
    expect(onChange).toHaveBeenCalledWith("siberia-3");
  });
});
