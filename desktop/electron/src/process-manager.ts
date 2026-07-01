import { ChildProcess, spawn } from "child_process";
import path from "path";

import { DesktopEnv, toProcessEnv } from "./env-manager";
import {
  createLogStream,
  isPortOpen,
  tailLogFile,
  waitForApiHealthy,
  waitForFrontendReady,
  waitForPort,
} from "./health";
import { resolveNodeRuntime } from "./node-runtime";
import {
  DesktopPaths,
  frontendNodeModulesExists,
  getApiPort,
  getFrontendDevPort,
  getFrontendProdPort,
  getSurrealPort,
} from "./paths";

export type StatusCallback = (message: string) => void;

interface ManagedService {
  name: string;
  process: ChildProcess;
  logPath: string;
}

export class ProcessManager {
  private services: ManagedService[] = [];
  private started = false;

  constructor(
    private readonly paths: DesktopPaths,
    private readonly desktopEnv: DesktopEnv,
    private readonly onStatus: StatusCallback
  ) {}

  async start(): Promise<void> {
    if (this.started) {
      return;
    }
    this.started = true;

    await this.startSurrealDb();
    await this.startApi();
    await this.startWorker();
    await this.startFrontend();
  }

  async stop(): Promise<void> {
    const reversed = [...this.services].reverse();
    for (const service of reversed) {
      await this.stopService(service);
    }
    this.services = [];
    this.started = false;
  }

  private async startSurrealDb(): Promise<void> {
    const port = getSurrealPort();
    const host = "127.0.0.1";

    if (process.env.OPEN_NOTEBOOK_SKIP_SURREAL === "1") {
      this.onStatus("Using external SurrealDB…");
      await this.waitForPortWithProgress("SurrealDB", host, port, 120_000);
      return;
    }

    if (await isPortOpen(host, port)) {
      this.onStatus("SurrealDB already running…");
      return;
    }

    if (!this.paths.surrealBin) {
      throw new Error(
        "SurrealDB binary not found. Start SurrealDB v2 manually (Docker) or set OPEN_NOTEBOOK_SURREAL_BIN."
      );
    }

    this.onStatus("Starting SurrealDB…");
    const dbFile = path.join(this.paths.surrealDataDir, "mydatabase.db");
    const logPath = path.join(this.paths.logsDir, "surrealdb.log");
    const child = spawn(
      this.paths.surrealBin,
      [
        "start",
        "--log",
        "info",
        "--user",
        this.desktopEnv.SURREAL_USER,
        "--pass",
        this.desktopEnv.SURREAL_PASSWORD,
        "--bind",
        `${host}:${port}`,
        `rocksdb:${dbFile}`,
      ],
      {
        cwd: this.paths.surrealDataDir,
        env: toProcessEnv(this.desktopEnv),
        stdio: ["ignore", "pipe", "pipe"],
      }
    );

    await this.waitForChildPort("SurrealDB", child, logPath, host, port, 120_000);
  }

  private async startApi(): Promise<void> {
    const port = getApiPort();
    const host = this.desktopEnv.API_HOST;
    const apiUrl = `http://${host}:${port}`;

    if (process.env.OPEN_NOTEBOOK_RESTART_SERVICES !== "1") {
      try {
        await waitForApiHealthy(apiUrl, 4_000);
        this.onStatus("API already running…");
        return;
      } catch {
        // spawn a fresh API below
      }
    }

    this.onStatus("Starting API…");
    const logPath = path.join(this.paths.logsDir, "api.log");
    const env = toProcessEnv(this.desktopEnv);
    const useFrozen =
      this.paths.apiBin &&
      (this.paths.isPackaged || process.env.OPEN_NOTEBOOK_USE_FROZEN !== "0");

    const child =
      useFrozen && this.paths.apiBin
        ? spawn(this.paths.apiBin, [], {
            cwd: path.dirname(this.paths.apiBin),
            env,
            stdio: ["ignore", "pipe", "pipe"],
          })
        : spawn(
            "uv",
            [
              "run",
              "--project",
              this.paths.repoRoot,
              "python",
              path.join(this.paths.repoRoot, "desktop", "entry_api.py"),
            ],
            {
            cwd: this.paths.repoRoot,
            env,
            stdio: ["ignore", "pipe", "pipe"],
          });

    this.pipeLogs(child, logPath);
    this.services.push({ name: "api", process: child, logPath });

    await this.waitForApiWithProgress(apiUrl, 240_000, child, logPath);
  }

  private async startWorker(): Promise<void> {
    this.onStatus("Starting worker…");
    const logPath = path.join(this.paths.logsDir, "worker.log");
    const env = toProcessEnv(this.desktopEnv);
    const useFrozen =
      this.paths.workerBin &&
      (this.paths.isPackaged || process.env.OPEN_NOTEBOOK_USE_FROZEN !== "0");

    const child =
      useFrozen && this.paths.workerBin
        ? spawn(this.paths.workerBin, [], {
            cwd: path.dirname(this.paths.workerBin),
            env,
            stdio: ["ignore", "pipe", "pipe"],
          })
        : spawn(
            "uv",
            [
              "run",
              "--project",
              this.paths.repoRoot,
              "python",
              path.join(this.paths.repoRoot, "desktop", "entry_worker.py"),
            ],
            {
            cwd: this.paths.repoRoot,
            env,
            stdio: ["ignore", "pipe", "pipe"],
          });

    this.pipeLogs(child, logPath);
    this.services.push({ name: "worker", process: child, logPath });

    // Worker has no HTTP port — brief pause so it can register commands.
    await sleep(2_000);
  }

  private async startFrontend(): Promise<void> {
    if (this.paths.useStandaloneFrontend) {
      await this.startStandaloneFrontend();
      return;
    }
    await this.startDevFrontend();
  }

  private async startDevFrontend(): Promise<void> {
    if (!frontendNodeModulesExists(this.paths)) {
      throw new Error(
        "Frontend dependencies missing. Run: cd frontend && npm install"
      );
    }

    const port = getFrontendDevPort();
    if (process.env.OPEN_NOTEBOOK_RESTART_SERVICES !== "1") {
      if (await isPortOpen("127.0.0.1", port)) {
        this.onStatus("Frontend already running…");
        await waitForFrontendReady(
          this.paths.uiUrl,
          `http://${this.desktopEnv.API_HOST}:${getApiPort()}`,
          30_000
        );
        return;
      }
    }

    this.onStatus("Starting frontend (dev)…");
    const logPath = path.join(this.paths.logsDir, "frontend.log");
    const env = {
      ...toProcessEnv(this.desktopEnv),
      PORT: String(port),
      HOSTNAME: "127.0.0.1",
      INTERNAL_API_URL: this.desktopEnv.INTERNAL_API_URL,
    };

    const nextBin = path.join(this.paths.frontendDir, "node_modules", ".bin", "next");
    const child = spawn(
      nextBin,
      ["dev", "--hostname", "127.0.0.1", "--port", String(port)],
      {
        cwd: this.paths.frontendDir,
        env,
        stdio: ["ignore", "pipe", "pipe"],
      }
    );

    await this.waitForChildPort("Frontend (dev)", child, logPath, "127.0.0.1", port, 300_000);
    this.onStatus("Waiting for frontend…");
    await waitForFrontendReady(
      this.paths.uiUrl,
      `http://${this.desktopEnv.API_HOST}:${getApiPort()}`,
      300_000
    );
  }

  private async startStandaloneFrontend(): Promise<void> {
    if (!this.paths.frontendStandaloneServer || !this.paths.frontendStandaloneDir) {
      throw new Error(
        "Standalone frontend not found. Run: bash desktop/build_frontend.sh"
      );
    }

    const port = getFrontendProdPort();
    if (process.env.OPEN_NOTEBOOK_RESTART_SERVICES !== "1") {
      if (await isPortOpen("127.0.0.1", port)) {
        this.onStatus("Frontend already running…");
        await waitForFrontendReady(
          this.paths.uiUrl,
          `http://${this.desktopEnv.API_HOST}:${getApiPort()}`,
          30_000
        );
        return;
      }
    }

    this.onStatus("Starting frontend (production)…");
    const logPath = path.join(this.paths.logsDir, "frontend.log");
    const node = resolveNodeRuntime();
    const env = {
      ...toProcessEnv(this.desktopEnv),
      ...node.extraEnv,
      PORT: String(port),
      HOSTNAME: "127.0.0.1",
      NODE_ENV: "production",
      INTERNAL_API_URL: this.desktopEnv.INTERNAL_API_URL,
    };

    const child = spawn(node.command, [...node.argsPrefix, "server.js"], {
      cwd: this.paths.frontendStandaloneDir,
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    await this.waitForChildPort(
      "Frontend (production)",
      child,
      logPath,
      "127.0.0.1",
      port,
      300_000
    );
    this.onStatus("Waiting for frontend…");
    await waitForFrontendReady(
      this.paths.uiUrl,
      `http://${this.desktopEnv.API_HOST}:${getApiPort()}`,
      60_000
    );
  }

  private async waitForPortWithProgress(
    label: string,
    host: string,
    port: number,
    timeoutMs: number
  ): Promise<void> {
    await waitForPort(host, port, timeoutMs, 500, (elapsedMs) => {
      const seconds = Math.floor(elapsedMs / 1000);
      if (seconds > 0 && seconds % 3 === 0) {
        this.onStatus(`Waiting for ${label}… (${seconds}s)`);
      }
    });
  }

  private async waitForApiWithProgress(
    apiUrl: string,
    timeoutMs: number,
    child: ChildProcess,
    logPath: string
  ): Promise<void> {
    const started = Date.now();
    const deadline = started + timeoutMs;
    let lastError = "API not reachable";

    while (Date.now() < deadline) {
      this.throwIfChildExited(child, "API", logPath);

      try {
        await waitForApiHealthy(apiUrl, 3_000);
        return;
      } catch (err) {
        lastError = err instanceof Error ? err.message : String(err);
      }

      const seconds = Math.floor((Date.now() - started) / 1000);
      if (seconds > 0 && seconds % 5 === 0) {
        this.onStatus(`Starting API… (${seconds}s, PyInstaller can take ~1 min)`);
      }
      await sleep(1_000);
    }

    throw new Error(`API health check failed: ${lastError}\n${tailLogFile(logPath)}`);
  }

  private async waitForChildPort(
    label: string,
    child: ChildProcess,
    logPath: string,
    host: string,
    port: number,
    timeoutMs: number
  ): Promise<void> {
    this.pipeLogs(child, logPath);
    this.services.push({ name: label.toLowerCase(), process: child, logPath });

    const started = Date.now();
    try {
      await waitForPort(host, port, timeoutMs, 500, (elapsedMs) => {
        this.throwIfChildExited(child, label, logPath);
        const seconds = Math.floor(elapsedMs / 1000);
        if (seconds > 0 && seconds % 3 === 0) {
          this.onStatus(`${label}… (${seconds}s)`);
        }
      });
    } catch (err) {
      this.throwIfChildExited(child, label, logPath);
      throw err;
    }
  }

  private throwIfChildExited(child: ChildProcess, label: string, logPath: string): void {
    if (child.exitCode === null && !child.killed) {
      return;
    }
    throw new Error(
      `${label} process exited (code ${child.exitCode ?? "unknown"}).\n${tailLogFile(logPath)}`
    );
  }

  private pipeLogs(child: ChildProcess, logPath: string): void {
    const stream = createLogStream(logPath);
    child.stdout?.on("data", (chunk: Buffer) => stream.write(chunk));
    child.stderr?.on("data", (chunk: Buffer) => stream.write(chunk));
    child.on("close", () => stream.end());
  }

  private async stopService(service: ManagedService): Promise<void> {
    if (service.process.killed || service.process.exitCode !== null) {
      return;
    }

    service.process.kill("SIGTERM");
    await waitForExit(service.process, 8000);
    if (service.process.exitCode === null) {
      service.process.kill("SIGKILL");
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitForExit(child: ChildProcess, timeoutMs: number): Promise<void> {
  return new Promise((resolve) => {
    if (child.exitCode !== null) {
      resolve();
      return;
    }

    const timer = setTimeout(() => resolve(), timeoutMs);
    child.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}
