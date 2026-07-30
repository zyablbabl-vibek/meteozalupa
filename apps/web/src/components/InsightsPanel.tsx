import type { InsightsResponse, WeatherInsight } from "../types/weather";

const LEVELS = {
  info: "Информация",
  attention: "Обратите внимание",
  notable: "Заметное явление",
};

function InsightCard({ item }: { item: WeatherInsight }) {
  return (
    <article className={`insight insight-${item.severity}`}>
      <span className="insight-level">{LEVELS[item.severity]}</span>
      <h3>{item.title}</h3>
      <p>{item.description}</p>
      <small>
        {item.models.length === 1
          ? "Показывает 1 из 3 моделей"
          : `Подтверждают ${item.models.length} из 3 моделей`}
      </small>
      <details>
        <summary>Почему это выделено?</summary>
        <p>{item.explanation}</p>
      </details>
    </article>
  );
}

export function InsightsPanel({
  data,
  category = "all",
}: {
  data: InsightsResponse;
  category?: "all" | "precipitation" | "wind";
}) {
  const groups = [
    ["precipitation", "Осадки", data.precipitation.items],
    ["wind", "Ветер", data.wind.items],
  ] as const;
  return (
    <section className="insights-panel">
      <span className="eyebrow">Автоматическая аналитика</span>
      <h2>На что обратить внимание</h2>
      <p className="insight-disclaimer">{data.disclaimer}</p>
      {groups
        .filter(([id]) => category === "all" || category === id)
        .map(([id, label, items]) => (
          <div key={id} className="insight-group">
            <h3>{label}</h3>
            {items.length ? (
              <div className="insight-grid">
                {items.map((item) => (
                  <InsightCard
                    key={`${item.reason_code}-${item.point_id}-${item.period_start}`}
                    item={item}
                  />
                ))}
              </div>
            ) : (
              <p>
                Модели не выделяют заметных особенностей по{" "}
                {id === "wind" ? "ветру" : "осадкам"} на выбранный период.
              </p>
            )}
          </div>
        ))}
    </section>
  );
}
