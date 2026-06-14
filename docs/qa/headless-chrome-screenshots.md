# Headless Chrome Screenshot Acceptance

At task close-out, provide a screenshot captured by headless Chrome whenever a browser-renderable project surface is available.

## Default Target

- For this project, prefer the React web platform at `http://localhost:5173`.
- Start it with `./scripts/run_app.sh` when it is not already running.
- Use the legacy Streamlit web console at `http://localhost:8501` only when the task explicitly targets legacy Streamlit.
- Use a local output path such as `/tmp/ai_trade_system_acceptance.png`.

## Required Evidence

- Wait until the page has rendered real project content, not only a loading shell.
- Include the screenshot as a Markdown image in the final response with an absolute local path.
- If the task has no browser-renderable surface, or Chrome cannot capture the page, report the exact not-applicable reason or blocker.

## Simple Command

Use this form for pages that render without asynchronous delays:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new \
  --disable-gpu \
  --hide-scrollbars \
  --no-first-run \
  --window-size=1440,1024 \
  --timeout=20000 \
  --screenshot=/tmp/ai_trade_system_acceptance.png \
  http://localhost:5173
```

## Repeatable React Platform Script

Use the repository script when responsive desktop plus narrow screenshots are needed:

```bash
node scripts/capture_app_screenshots.mjs
```

Defaults:

- Target URL: `http://localhost:5173`
- Output directory: `/tmp`
- Output files:
  - `/tmp/ai_trade_system_desktop_1440.png`
  - `/tmp/ai_trade_system_mobile_390.png`

Options:

```bash
node scripts/capture_app_screenshots.mjs \
  --url http://localhost:5173 \
  --out-dir /tmp \
  --prefix ai_trade_system_round_10
```

The script launches headless Chrome through DevTools Protocol, waits for `.app-shell`, `.content-shell`, and `AI量化平台` text, captures 1440x1024 and 390x844 viewports, writes PNG files, and prints the measured PNG dimensions as JSON.

## Robust Capture

For Streamlit or other asynchronous pages, prefer a Chrome DevTools Protocol flow:

1. Launch Chrome with `--headless=new`, `--remote-debugging-port`, and a temporary `--user-data-dir`.
2. Navigate to the target page.
3. Poll `document.body.innerText` or stable selectors until real page content appears.
4. Call `Page.captureScreenshot` and write the PNG to `/tmp`.
5. Verify the PNG dimensions and visually inspect it before final response.

This avoids returning screenshots of Streamlit loading skeletons.
