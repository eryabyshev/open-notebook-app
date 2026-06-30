import fs from "fs";
import net from "net";
import path from "path";

export async function isPortOpen(host: string, port: number, timeoutMs = 1500): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    const done = (result: boolean) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(result);
    };

    socket.setTimeout(timeoutMs);
    socket.once("connect", () => done(true));
    socket.once("timeout", () => done(false));
    socket.once("error", () => done(false));
  });
}

export async function waitForPort(
  host: string,
  port: number,
  timeoutMs: number,
  intervalMs = 500,
  onTick?: (elapsedMs: number) => void
): Promise<void> {
  const started = Date.now();
  const deadline = started + timeoutMs;
  while (Date.now() < deadline) {
    if (await isPortOpen(host, port)) {
      return;
    }
    onTick?.(Date.now() - started);
    await sleep(intervalMs);
  }
  throw new Error(`Timed out waiting for ${host}:${port}`);
}

export interface ApiConfigResponse {
  dbStatus?: string;
  version?: string;
}

export async function waitForHttpOk(
  url: string,
  timeoutMs: number,
  intervalMs = 750
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError = "No response";

  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (response.ok) {
        return;
      }
      lastError = `HTTP ${response.status}`;
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
    await sleep(intervalMs);
  }

  throw new Error(`Timed out waiting for ${url}: ${lastError}`);
}

export async function waitForFrontendReady(
  uiUrl: string,
  apiUrl: string,
  timeoutMs: number
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError = "Frontend not ready";

  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${uiUrl}/api/config`, {
        signal: AbortSignal.timeout(8000),
      });
      if (response.ok) {
        const body = (await response.json()) as ApiConfigResponse;
        if (body.dbStatus === "online") {
          return;
        }
        lastError = `Database status: ${body.dbStatus ?? "unknown"}`;
      } else {
        lastError = `Frontend proxy returned HTTP ${response.status}`;
      }
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }

    await sleep(500);
  }

  throw new Error(`Frontend health check failed: ${lastError}`);
}

export async function waitForApiHealthy(
  apiUrl: string,
  timeoutMs: number,
  intervalMs = 750
): Promise<ApiConfigResponse> {
  const deadline = Date.now() + timeoutMs;
  let lastError = "API not reachable";

  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${apiUrl}/api/config`, {
        signal: AbortSignal.timeout(3000),
      });
      if (!response.ok) {
        lastError = `HTTP ${response.status}`;
      } else {
        const body = (await response.json()) as ApiConfigResponse;
        if (body.dbStatus === "online") {
          return body;
        }
        lastError = `Database status: ${body.dbStatus ?? "unknown"}`;
      }
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
    await sleep(intervalMs);
  }

  throw new Error(`API health check failed: ${lastError}`);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function tailLogFile(logPath: string, maxLines = 12): string {
  try {
    if (!fs.existsSync(logPath)) {
      return "(log file empty)";
    }
    const lines = fs.readFileSync(logPath, "utf-8").split("\n").filter(Boolean);
    return lines.slice(-maxLines).join("\n");
  } catch {
    return "(could not read log file)";
  }
}

export function createLogStream(logPath: string): fs.WriteStream {
  fs.mkdirSync(path.dirname(logPath), { recursive: true });
  return fs.createWriteStream(logPath, { flags: "a" });
}
