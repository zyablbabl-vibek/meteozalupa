import type { Region } from "../types/weather";

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
  return (
    <div className="state region-state">
      <div className="loader" />
      <h2>Загружаем {name}</h2>
      <p>Проверяем семидневный кэш выбранного региона.</p>
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
