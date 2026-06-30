import { app } from "electron";
import fs from "fs";
import path from "path";

export interface DesktopPaths {
  repoRoot: string;
  userDataDir: string;
  dataFolder: string;
  logsDir: string;
  desktopEnvFile: string;
  surrealDataDir: string;
  frontendDir: string;
  apiBundleDir: string;
  workerBundleDir: string;
  resourcesDir: string;
  surrealBin: string | null;
  apiBin: string | null;
  workerBin: string | null;
  frontendStandaloneServer: string | null;
  isPackaged: boolean;
  isDev: boolean;
  uiUrl: string;
}

const FRONTEND_DEV_PORT = 3000;
const FRONTEND_PROD_PORT = 8502;
const API_PORT = 5055;
const SURREAL_PORT = 8000;

export function getApiPort(): number {
  return API_PORT;
}

export function getSurrealPort(): number {
  return SURREAL_PORT;
}

export function getFrontendDevPort(): number {
  return FRONTEND_DEV_PORT;
}

export function getFrontendProdPort(): number {
  return FRONTEND_PROD_PORT;
}

export function resolveDesktopPaths(): DesktopPaths {
  const isPackaged = app.isPackaged;
  const isDev = !isPackaged;

  const repoRoot = isPackaged
    ? path.resolve(process.resourcesPath, "..", "..")
    : path.resolve(__dirname, "..", "..", "..");

  const userDataDir = app.getPath("userData");
  const dataFolder = path.join(userDataDir, "data");
  const logsDir = path.join(userDataDir, "logs");
  const desktopEnvFile = path.join(userDataDir, "desktop.env");
  const surrealDataDir = path.join(dataFolder, "surrealdb");

  const resourcesDir = isPackaged
    ? process.resourcesPath
    : path.join(repoRoot, "desktop", "resources");

  const frontendDir = path.join(repoRoot, "frontend");

  const apiBundleDir = isPackaged
    ? path.join(resourcesDir, "api")
    : path.join(repoRoot, "desktop", "dist", "open-notebook-api");

  const workerBundleDir = isPackaged
    ? path.join(resourcesDir, "worker")
    : path.join(repoRoot, "desktop", "dist", "open-notebook-worker");

  const apiBinName = process.platform === "win32" ? "open-notebook-api.exe" : "open-notebook-api";
  const workerBinName =
    process.platform === "win32" ? "open-notebook-worker.exe" : "open-notebook-worker";

  const apiBinCandidate = path.join(apiBundleDir, apiBinName);
  const workerBinCandidate = path.join(workerBundleDir, workerBinName);

  const apiBin = fs.existsSync(apiBinCandidate) ? apiBinCandidate : null;
  const workerBin = fs.existsSync(workerBinCandidate) ? workerBinCandidate : null;

  const surrealBinName = process.platform === "win32" ? "surreal.exe" : "surreal";
  const surrealBin = resolveSurrealBin(resourcesDir, surrealBinName);

  const frontendStandaloneServer = path.join(
    frontendDir,
    ".next",
    "standalone",
    "server.js"
  );
  const hasStandalone = fs.existsSync(frontendStandaloneServer);

  const useDevFrontend =
    isDev && process.env.OPEN_NOTEBOOK_FRONTEND_MODE !== "standalone";

  const uiPort = useDevFrontend ? FRONTEND_DEV_PORT : FRONTEND_PROD_PORT;
  const uiUrl = `http://localhost:${uiPort}`;

  return {
    repoRoot,
    userDataDir,
    dataFolder,
    logsDir,
    desktopEnvFile,
    surrealDataDir,
    frontendDir,
    apiBundleDir,
    workerBundleDir,
    resourcesDir,
    surrealBin,
    apiBin,
    workerBin,
    frontendStandaloneServer: hasStandalone ? frontendStandaloneServer : null,
    isPackaged,
    isDev,
    uiUrl,
  };
}

function resolveSurrealBin(resourcesDir: string, binName: string): string | null {
  const envBin = process.env.OPEN_NOTEBOOK_SURREAL_BIN?.trim();
  if (envBin && fs.existsSync(envBin)) {
    return envBin;
  }

  const bundled = path.join(resourcesDir, "surrealdb", binName);
  if (fs.existsSync(bundled)) {
    return bundled;
  }

  return null;
}

export function ensureDataDirs(paths: DesktopPaths): void {
  fs.mkdirSync(paths.dataFolder, { recursive: true });
  fs.mkdirSync(paths.logsDir, { recursive: true });
  fs.mkdirSync(paths.surrealDataDir, { recursive: true });
}

export function frontendNodeModulesExists(paths: DesktopPaths): boolean {
  return fs.existsSync(path.join(paths.frontendDir, "node_modules", ".bin", "next"));
}
