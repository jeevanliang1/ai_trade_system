# Portfolio Signal Breakdown QA

Date: 2026-06-14

## Scope

Completed the Portfolio Lab signal breakdown module for portfolio previews.

## Evidence

- Added backend contribution tracking for each raw strategy signal before portfolio aggregation.
- Added API contract coverage for `/api/portfolio/preview` returning `breakdown.contributions` and indexed allocation metadata.
- Added Portfolio Lab test coverage for the rendered signal breakdown panel.
- Ran `python -m pytest tests/test_portfolio.py -q`: 4 tests passed.
- Ran `npm test -- PortfolioPage.test.tsx`: 4 tests passed.
- Ran `python -m pytest`: 55 tests passed.
- Ran `npm test`: 11 files and 30 tests passed.
- Ran `npm run build`: Vite production build succeeded.
- Browser QA used the in-app Browser at `http://127.0.0.1:5174/` because `5173` was occupied by an existing Vite process; the Browser runtime verified page identity, rendered content, no framework overlay, no console errors, and the interaction path `组合实验室 -> 预览组合信号 -> 信号拆解`.
- In-app Browser full-page screenshot timed out on `Page.captureScreenshot`, so the required PNG evidence was captured with system Chrome after repeating the same interaction.
- Acceptance screenshot: `/tmp/ai_trade_system_portfolio_breakdown_acceptance.png`.

## Notes

The screenshot is viewport-focused after scrolling `.signal-breakdown-panel` into view because the app uses internal scroll containers and full-page Chrome capture did not frame the new panel clearly.
