# AI Researcher Evidence Groups QA

Date: 2026-06-14

## Scope

- AI Researcher now renders generated technical evidence, information-side evidence, and risk warnings as separate groups in the React platform.
- The prompt snapshot audit panel remains collapsed by default below the grouped evidence.

## Verification

- `cd frontend && npm test -- src/pages/AIPage.test.tsx`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- `python -m pytest -q`
- In-app Browser validation: loaded `http://127.0.0.1:5173`, opened AI Researcher, clicked `生成AI观点`, and confirmed `技术证据`, `信息面证据`, `风险提示`, and generated evidence text were visible with no console errors.
- Headless Chrome acceptance screenshot: `/tmp/ai_trade_system_ai_evidence_groups.png`

## Notes

- The in-app Browser interaction path succeeded, but its screenshot capture timed out on this run. The final acceptance image was captured with headless Chrome through the same AI Researcher interaction flow.
