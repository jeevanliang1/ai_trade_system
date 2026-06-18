# Signal Radar Volume Momentum QA

Date: 2026-06-19

## Scope

This QA pass covers the Signal Radar `volume_momentum` score mode, managed A-share CSV path resolution, React mode switching, diagnostic rendering, and CSV export fields.

## TDD Evidence

- Backend RED: `PYTHONPATH=src python -m pytest tests/test_api_routes.py -q`
  - Failed before implementation because batch responses did not include `score_mode`, `local_csv` still filtered legacy `data/{code}_daily.csv`, and `volume_momentum` mode was ignored.
- Backend GREEN: `PYTHONPATH=src python -m pytest tests/test_api_routes.py -q`
  - Result: `18 passed in 0.88s`.
- Frontend RED: `npm test -- SignalRadarPage.test.tsx`
  - Failed before implementation because the page did not submit `score_mode`, had no `评分模式` control, and CSV export lacked momentum diagnostic columns.
- Frontend GREEN: `npm test -- SignalRadarPage.test.tsx`
  - Result: `5 passed`.

## Full Verification

- `PYTHONPATH=src python -m pytest`
  - Result: `97 passed in 3.57s`.
- `npm test` from `frontend/`
  - Result: `18 passed`, `85 passed`.
- `npm run build` from `frontend/`
  - Result: TypeScript and Vite production build succeeded.

## Browser Acceptance

- Server command: `./scripts/run_app.sh`
- Browser URL: `http://127.0.0.1:5173/`
- Browser workflow:
  1. Opened `信号雷达`.
  2. Entered query `688981`.
  3. Selected `评分模式 = 量价动量`.
  4. Ran `批量扫描`.
  5. Verified `688981 中芯国际` rendered in `量价动量排行` with `动量`, `放量`, and `趋势` diagnostic columns and detail-card rows.
- Console errors: `[]`
- Screenshot: `/tmp/ai_trade_system_signal_radar_volume_momentum.png`
