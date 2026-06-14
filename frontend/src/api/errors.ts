const LOCAL_API_CONNECTION_MESSAGE = "本地 API 未连接，请确认 ./scripts/run_app.sh 正在运行。";

export function formatRequestError(error: unknown): string {
  if (isNetworkFailure(error)) return LOCAL_API_CONNECTION_MESSAGE;
  if (error instanceof Error) return error.message;
  return "未知错误";
}

function isNetworkFailure(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return error.message === "Failed to fetch" || error.message === "NetworkError when attempting to fetch resource." || error.message === "Load failed";
}
