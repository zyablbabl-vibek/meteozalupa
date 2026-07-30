export const number = (value: number | null | undefined, digits = 1) =>
  value == null ? "—" : value.toFixed(digits);
export const temperature = (value: number | null | undefined) =>
  value == null ? "—" : `${value > 0 ? "+" : ""}${value.toFixed(1)}°`;
export const localDate = (timezone = "Asia/Yakutsk", offset = 0) => {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const base = new Date(
    `${parts.find((p) => p.type === "year")?.value}-${parts.find((p) => p.type === "month")?.value}-${parts.find((p) => p.type === "day")?.value}T00:00:00Z`,
  );
  base.setUTCDate(base.getUTCDate() + offset);
  return base.toISOString().slice(0, 10);
};
