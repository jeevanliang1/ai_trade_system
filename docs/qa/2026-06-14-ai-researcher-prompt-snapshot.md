# AI Researcher Prompt Snapshot QA

## Scope

- Persist the generated AI research prompt returned by `/api/ai/research`.
- Show the prompt on the AI Researcher page in a collapsible audit panel.
- Keep the panel collapsed by default and preserve line breaks for review.

## Verification

- `cd frontend && npm test -- src/pages/AIPage.test.tsx`
- `cd frontend && npm test`
- `cd frontend && npm run build`

## Evidence

- Targeted AIPage tests passed with 3 tests.
- Full frontend test suite passed with 42 tests.
- Frontend production build passed.
- Headless Chrome screenshot: `/tmp/ai_trade_system_ai_prompt_snapshot.png`

## Notes

- The prompt is stored as frontend state only; it is not written to disk or sent anywhere beyond the existing local API response.
