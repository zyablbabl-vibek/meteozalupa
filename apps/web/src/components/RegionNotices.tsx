import type { Region } from "../types/weather";
import { useEffect, useState } from "react";

export function RegionCoverageNotice({ region }: { region: Region }) {
  if (region.data_status === "verified") return null;
  return (
    <div className="warning coverage-notice">
      Прогноз рассчитан по {region.point_count} контрольным точкам. Набор имеет
      статус «частично проверен»: некоторые удалённые районы пока могут быть не
      представлены.
    </div>
  );
}

export function RegionTimezoneNotice({ region }: { region: Region }) {
  if (!region.has_multiple_timezones) return null;
  return (
    <div className="notice timezone-notice">
      Регион охватывает несколько часовых поясов. Общая дата интерфейса
      определяется по {region.primary_timezone}, а почасовые данные показываются
      по местному времени выбранной точки.
    </div>
  );
}

export function RegionLoadingState({ name }: { name: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [name]);

  const explanation =
    elapsed < 3
      ? "Ищем ранее сохранённый прогноз."
      : elapsed < 15
        ? "Если сохранённых данных ещё нет, получаем модели ECMWF, GFS и ICON из Open‑Meteo."
        : "Первое получение региона занимает больше времени. Запрос продолжается и завершится данными либо понятной ошибкой.";

  return (
    <div className="state region-state" aria-live="polite">
      <div className="loader" />
      <h2>Загружаем {name}</h2>
      <p>{explanation}</p>
      <strong>{elapsed} сек.</strong>
    </div>
  );
}

export function RegionErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="state error region-state">
      <h2>Не удалось загрузить регион</h2>
      <p>{message}</p>
      <button onClick={onRetry}>Повторить</button>
    </div>
  );
}
