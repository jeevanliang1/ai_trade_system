# AI Researcher Note Editor QA

Date: 2026-06-14

## Scope

Completed the AI Researcher information-note editor module.

## Evidence

- Replaced the single plain `信息面摘要` textarea with separate recent-note rows.
- Added `新增信息面摘要` and per-row delete controls so users can adjust the note list before generating research.
- Kept the API action contract unchanged: `researchAI` still receives `notes: string[]`, prompt mode, and horizon.
- Submitted notes are trimmed and empty rows are ignored.
- Added focused `AIPage` tests for row editing, non-empty submission, row addition, and row removal.
- Ran `npm test -- src/pages/AIPage.test.tsx`: 2 tests passed.
- Ran `npm test`: 12 files and 41 tests passed.
- Ran `npm run build`: Vite production build succeeded.
- Ran `python -m pytest`: 56 tests passed.
- Browser QA used the in-app Browser at `http://127.0.0.1:5174/` because `5173` was occupied by an existing Vite process; it verified page identity, nonblank content, no framework overlay, no console errors/warnings, AI Researcher navigation, add/edit/delete note-row behavior, and generated evidence containing the edited notes.
- In-app Browser screenshot capture timed out on `Page.captureScreenshot`; the required PNG evidence was captured with headless system Chrome after repeating the same AI note flow through Chrome DevTools Protocol.
- Acceptance screenshot: `docs/qa/screenshots/2026-06-14-ai-researcher-note-editor.png`.

## Notes

This is intentionally a frontend-scoped module. The existing FastAPI `/api/ai/research` endpoint already accepts multiple information notes, and the app shell already forwards the note array.
