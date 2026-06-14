# Portfolio AI Weight Preview QA

Date: 2026-06-14

## Scope

Completed the Portfolio Lab AI-adjust preview module for portfolio previews.

## Evidence

- Added backend portfolio preview metadata for `ai_adjustment` and per-allocation `base_weight`, `adjusted_weight`, `ai_delta`, and `ai_adjusted`.
- Added API contract coverage for `/api/portfolio/preview` returning the AI-adjusted allocation view.
- Added Portfolio Lab test coverage for the rendered AI weight preview panel.
- Ran `python -m pytest tests/test_api_routes.py::test_portfolio_preview_returns_ai_adjustment_weight_preview -q`: 1 test passed.
- Ran `npm test -- PortfolioPage.test.tsx -t "AI-adjust"`: 1 test passed and 4 tests skipped by filter.
- Ran `npm test -- PortfolioPage.test.tsx`: 5 tests passed.
- Ran `python -m pytest tests/test_api_routes.py -q`: 6 tests passed.
- Ran `npm test`: 11 files and 31 tests passed.
- Ran `python -m pytest`: 56 tests passed.
- Ran `npm run build`: Vite production build succeeded.
- Browser QA used the in-app Browser at `http://127.0.0.1:5174/` because `5173` was occupied by an existing Vite process; it verified the interaction path `组合实验室 -> AI参与评分 -> AI研究员 -> 生成AI观点 -> 组合实验室 -> 预览组合信号`.
- The in-app Browser verified `AI权重预览`, `方向：看多`, `1.00 -> 1.05`, and `+0.05` with no console errors reported by the page check.
- In-app Browser screenshot capture timed out on `Page.captureScreenshot`; the required PNG evidence was captured with system Chrome after repeating the same interaction.
- Acceptance screenshot: `docs/qa/screenshots/2026-06-14-portfolio-ai-weight-preview.png`.

## Notes

The preview intentionally shows raw allocation weight before/after values. For bullish AI scoring, each enabled allocation receives a `+0.05` adjustment before portfolio signal aggregation.
