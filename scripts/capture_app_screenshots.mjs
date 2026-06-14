#!/usr/bin/env node
import { createServer } from "node:net";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";

const DEFAULT_URL = "http://localhost:5173";
const DEFAULT_OUT_DIR = "/tmp";
const DEFAULT_PREFIX = "ai_trade_system";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const args = parseArgs(process.argv.slice(2));
const url = args.url ?? DEFAULT_URL;
const outDir = args["out-dir"] ?? DEFAULT_OUT_DIR;
const prefix = args.prefix ?? DEFAULT_PREFIX;

const captures = [
  { name: "desktop_1440", width: 1440, height: 1024, mobile: false },
  { name: "mobile_390", width: 390, height: 844, mobile: true }
];

let chrome;
let userDataDir;

async function main() {
  try {
    await mkdir(outDir, { recursive: true });
    userDataDir = await mkdtemp(join(tmpdir(), "ai-trade-system-chrome-"));
    const port = await freePort();
    chrome = spawn(CHROME, [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${userDataDir}`,
      "about:blank"
    ], { stdio: "ignore" });

    const wsUrl = await waitForPageWebSocketUrl(port);
    const cdp = await CdpClient.connect(wsUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    const results = [];
    for (const capture of captures) {
      const path = join(outDir, `${prefix}_${capture.name}.png`);
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: capture.width,
        height: capture.height,
        deviceScaleFactor: 1,
        mobile: capture.mobile
      });
      await cdp.send("Page.navigate", { url });
      await waitForRenderedApp(cdp);
      const screenshot = await cdp.send("Page.captureScreenshot", { format: "png", fromSurface: true });
      await writeFile(path, Buffer.from(screenshot.data, "base64"));
      const dimensions = await pngDimensions(path);
      results.push({ path, ...dimensions });
    }

    console.log(JSON.stringify({ url, results }, null, 2));
    await cdp.close();
  } finally {
    if (chrome) {
      chrome.kill();
      await waitForExit(chrome);
    }
    if (userDataDir) await rm(userDataDir, { recursive: true, force: true });
  }
}

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const [key, inlineValue] = token.slice(2).split("=", 2);
    parsed[key] = inlineValue ?? argv[index + 1];
    if (inlineValue === undefined) index += 1;
  }
  return parsed;
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
    server.on("error", reject);
  });
}

async function waitForPageWebSocketUrl(port) {
  const endpoint = `http://127.0.0.1:${port}/json/list`;
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(endpoint);
      if (response.ok) {
        const payload = await response.json();
        const page = payload.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
        if (page) return page.webSocketDebuggerUrl;
      }
    } catch {
      // Chrome is still starting.
    }
    await delay(100);
  }
  throw new Error("Timed out waiting for Chrome DevTools endpoint");
}

async function waitForRenderedApp(cdp) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    const result = await cdp.send("Runtime.evaluate", {
      expression: `
        Boolean(
          document.querySelector(".app-shell") &&
          document.querySelector(".content-shell") &&
          document.body.innerText.includes("AI量化平台")
        )
      `,
      returnByValue: true
    });
    if (result.result?.value === true) return;
    await delay(200);
  }
  throw new Error("Timed out waiting for rendered app content");
}

async function pngDimensions(path) {
  const bytes = await readFile(path);
  if (bytes.toString("ascii", 1, 4) !== "PNG") {
    throw new Error(`Not a PNG file: ${path}`);
  }
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitForExit(child) {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve();
  return new Promise((resolve) => child.once("exit", resolve));
}

class CdpClient {
  static connect(url) {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(url);
      const client = new CdpClient(socket);
      socket.addEventListener("open", () => resolve(client), { once: true });
      socket.addEventListener("error", reject, { once: true });
      socket.addEventListener("message", (event) => client.handleMessage(event));
    });
  }

  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    this.socket.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  handleMessage(event) {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const pending = this.pending.get(message.id);
    if (!pending) return;
    this.pending.delete(message.id);
    if (message.error) {
      pending.reject(new Error(message.error.message));
    } else {
      pending.resolve(message.result);
    }
  }

  close() {
    this.socket.close();
  }
}

await main();
