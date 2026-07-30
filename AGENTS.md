# Руководство для агентов

- Backend: `apps/api`; frontend: `apps/web`; контрольные точки: `data`.
- Запуск: `docker compose up --build`.
- Backend: `cd apps/api && pytest && ruff check . && mypy app`.
- Frontend: `cd apps/web && npm test && npm run lint && npm run build`.
- Python форматируется Ruff, TypeScript — Prettier/ESLint.
- Никогда не смешивайте ряды ECMWF, GFS и ICON до статистического слоя.
- При изменении статистики обязательно добавляйте или обновляйте тесты.
- Пропущенные погодные значения нельзя подменять нулём.

