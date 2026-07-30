# Руководство для агентов

- Backend: `apps/api`; frontend: `apps/web`; registry и контрольные точки:
  `data/regions`.
- Запуск: `docker compose up --build`.
- Backend: `cd apps/api && pytest && ruff check . && mypy app`.
- Frontend: `cd apps/web && npm test && npm run lint && npm run build`.
- Python форматируется Ruff, TypeScript — Prettier/ESLint.
- Никогда не смешивайте ряды ECMWF, GFS и ICON до статистического слоя.
- При изменении статистики обязательно добавляйте или обновляйте тесты.
- Пропущенные погодные значения нельзя подменять нулём.
- Любой погодный запрос, кэш и агрегат должен быть ограничен одним `region_id`.
- Дневные агрегаты точки формируются по её IANA timezone; дата интерфейса — по
  `primary_timezone` выбранного региона.
- Не добавляйте выдуманные координаты и GeoJSON: сохраняйте источник и дату
  проверки либо явно оставляйте границу отсутствующей.
