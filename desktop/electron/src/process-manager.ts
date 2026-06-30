import { ChildProcess, spawn } from "child_process";
import fs from "fs";
import path from "path";

import { DesktopEnv, toProcessEnv } from "./env-manager";
import {
  createLogStream,
  isPortOpen,
  waitForApiHealthy,
  waitForFrontendReady,
  waitForPort,
} from "./health";
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
  private surrealManaged = false;

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
    this.surrealManaged = false;
  }

  private async startSurrealDb(): Promise<void> {
    const port = getSurrealPort();
    const host = "127.0.0.1";

    if (process.env.OPEN_NOTEBOOK_SKIP_SURREAL === "1") {
      this.onStatus("Using external SurrealDB…");
      await waitForPort(host, port, 120_000);
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
    const args = [
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
    ];

    const logPath = path.join(this.paths.logsDir, "surrealdb.log");
    const child = spawn(this.paths.surrealBin, args, {
      cwd: this.paths.surrealDataDir,
      env: toProcessEnv(this.desktopEnv),
      stdio: ["ignore", "pipe", "pipe"],
    });

    this.pipeLogs(child, logPath);
    this.services.push({ name: "surrealdb", process: child, logPath });
    this.surrealManaged = true;

    await waitForPort(host, port, 120_000);
  }

  private async startApi(): Promise<void> {
    this.onStatus("Starting API…");
    const port = getApiPort();
    const host = this.desktopEnv.API_HOST;
    const logPath = path.join(this.paths.logsDir, "api.log");
    const env = toProcessEnv(this.desktopEnv);

    const useFrozen =
      this.paths.apiBin &&
      (this.paths.isPackaged || process.env.OPEN_NOTEBOOK_USE_FROZEN !== "0");

    let child: ChildProcess;
    if (useFrozen && this.paths.apiBin) {
      child = spawn(this.paths.apiBin, [], {
        cwd: path.dirname(this.paths.apiBin),
        env,
        stdio: ["ignore", "pipe", "pipe"],
      });
    } else {
      child = spawn(
        "uv",
        ["run", "python", path.join("desktop", "entry_api.py")],
        {
          cwd: this.paths.repoRoot,
          env,
          stdio: ["ignore", "pipe", "pipe"],
        }
      );
    }

    this.pipeLogs(child, logPath);
    this.services.push({ name: "api", process: child, logPath });

    await waitForApiHealthy(`http://${host}:${port}`, 180_000);
  }

  private async startWorker(): Promise<void> {
    this.onStatus("Starting worker…");
    const logPath = path.join(this.paths.logsDir, "worker.log");
    const env = toProcessEnv(this.desktopEnv);

    const useFrozen =
      this.paths.workerBin &&
      (this.paths.isPackaged || process.env.OPEN_NOTEBOOK_USE_FROZEN !== "0");

    let child: ChildProcess;
    if (useFrozen && this.paths.workerBin) {
      child = spawn(this.paths.workerBin, [], {
        cwd: path.dirname(this.paths.workerBin),
        env,
        stdio: ["ignore", "pipe", "pipe"],
      });
    } else {
      child = spawn(
        "uv",
        ["run", "python", path.join("desktop", "entry_worker.py")],
        {
          cwd: this.paths.repoRoot,
          env,
          stdio: ["ignore", "pipe", "pipe"],
        }
      );
    }

    this.pipeLogs(child, logPath);
    this.services.push({ name: "worker", process: child, logPath });

    await waitForPort("127.0.0.1", getApiPort(), 30_000);
  }

  private async startFrontend(): Promise<void> {
    const useDevFrontend =
      this.paths.isDev && process.env.OPEN_NOTEBOOK_FRONTEND_MODE !== "standalone";

    if (useDevFrontend) {
      if (!frontendNodeModulesExists(this.paths)) {
        throw new Error(
          "Frontend dependencies missing. Run: cd frontend && npm install"
        );
      }

      this.onStatus("Starting frontend (dev)…");
      const logPath = path.join(this.paths.logsDir, "frontend.log");
      const port = getFrontendDevPort();
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

      this.pipeLogs(child, logPath);
      this.services.push({ name: "frontend", process: child, logPath });
      await waitForPort("127.0.0.1", port, 180_000);
      this.onStatus("Waiting for frontend…");
      await waitForFrontendReady(
        this.paths.uiUrl,
        `http://${this.desktopEnv.API_HOST}:${getApiPort()}`,
        300_000
      );
      return;
    }

    if (!this.paths.frontendStandaloneServer) {
      throw new Error(
        "Next.js standalone build not found. Run: cd frontend && npm run build"
      );
    }

    this.onStatus("Starting frontend…");
    const logPath = path.join(this.paths.logsDir, "frontend.log");
    const standaloneDir = path.dirname(this.paths.frontendStandaloneServer);
    const env = {
      ...toProcessEnv(this.desktopEnv),
      PORT: String(getFrontendProdPort()),
      HOSTNAME: "127.0.0.1",
      NODE_ENV: "production",
    };

    const child = spawn(process.execPath, ["server.js"], {
      cwd: standaloneDir,
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    this.pipeLogs(child, logPath);
    this.services.push({ name: "frontend", process: child, logPath });
    await waitForPort("127.0.0.1", getFrontendProdPort(), 180_000);
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
