import crypto from "crypto";
import fs from "fs";
import path from "path";

export interface DesktopEnv {
  OPEN_NOTEBOOK_ENCRYPTION_KEY: string;
  SURREAL_URL: string;
  SURREAL_USER: string;
  SURREAL_PASSWORD: string;
  SURREAL_NAMESPACE: string;
  SURREAL_DATABASE: string;
  DATA_FOLDER: string;
  API_HOST: string;
  API_PORT: string;
  INTERNAL_API_URL: string;
  TIKTOKEN_CACHE_DIR: string;
}

export function loadOrCreateDesktopEnv(
  envFile: string,
  dataFolder: string,
  repoRoot?: string,
  isDev = false
): DesktopEnv {
  let env: DesktopEnv;
  if (fs.existsSync(envFile)) {
    env = parseEnvFile(fs.readFileSync(envFile, "utf-8"), dataFolder);
  } else {
    env = createDefaultEnv(dataFolder);
    fs.writeFileSync(envFile, serializeEnv(env), { mode: 0o600 });
  }

  if (isDev && repoRoot) {
    env = applyRepoEnvOverrides(env, repoRoot);
  }

  return env;
}

function applyRepoEnvOverrides(env: DesktopEnv, repoRoot: string): DesktopEnv {
  const repoEnvPath = path.join(repoRoot, ".env");
  if (!fs.existsSync(repoEnvPath)) {
    return env;
  }

  const repoValues = parseRawEnv(fs.readFileSync(repoEnvPath, "utf-8"));
  const surrealKeys = [
    "SURREAL_URL",
    "SURREAL_USER",
    "SURREAL_PASSWORD",
    "SURREAL_NAMESPACE",
    "SURREAL_DATABASE",
    "OPEN_NOTEBOOK_ENCRYPTION_KEY",
  ] as const;

  const merged = { ...env };
  for (const key of surrealKeys) {
    if (repoValues[key]) {
      merged[key] = repoValues[key];
    }
  }
  return merged;
}

function parseRawEnv(content: string): Record<string, string> {
  const values: Record<string, string> = {};
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim().replace(/^["']|["']$/g, "");
    values[key] = value;
  }
  return values;
}

function createDefaultEnv(dataFolder: string): DesktopEnv {
  const surrealUser = `on_${crypto.randomBytes(4).toString("hex")}`;
  const surrealPassword = crypto.randomBytes(24).toString("base64url");
  const encryptionKey = crypto.randomBytes(32).toString("base64url");

  return {
    OPEN_NOTEBOOK_ENCRYPTION_KEY: encryptionKey,
    SURREAL_URL: "ws://127.0.0.1:8000/rpc",
    SURREAL_USER: surrealUser,
    SURREAL_PASSWORD: surrealPassword,
    SURREAL_NAMESPACE: "open_notebook",
    SURREAL_DATABASE: "open_notebook",
    DATA_FOLDER: dataFolder,
    API_HOST: "127.0.0.1",
    API_PORT: "5055",
    INTERNAL_API_URL: "http://127.0.0.1:5055",
    TIKTOKEN_CACHE_DIR: `${dataFolder}/tiktoken-cache`,
  };
}

function parseEnvFile(content: string, dataFolder: string): DesktopEnv {
  const values: Record<string, string> = {};
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim().replace(/^["']|["']$/g, "");
    values[key] = value;
  }

  const defaults = createDefaultEnv(dataFolder);
  return {
    OPEN_NOTEBOOK_ENCRYPTION_KEY:
      values.OPEN_NOTEBOOK_ENCRYPTION_KEY ?? defaults.OPEN_NOTEBOOK_ENCRYPTION_KEY,
    SURREAL_URL: values.SURREAL_URL ?? defaults.SURREAL_URL,
    SURREAL_USER: values.SURREAL_USER ?? defaults.SURREAL_USER,
    SURREAL_PASSWORD: values.SURREAL_PASSWORD ?? defaults.SURREAL_PASSWORD,
    SURREAL_NAMESPACE: values.SURREAL_NAMESPACE ?? defaults.SURREAL_NAMESPACE,
    SURREAL_DATABASE: values.SURREAL_DATABASE ?? defaults.SURREAL_DATABASE,
    DATA_FOLDER: values.DATA_FOLDER ?? dataFolder,
    API_HOST: values.API_HOST ?? defaults.API_HOST,
    API_PORT: values.API_PORT ?? defaults.API_PORT,
    INTERNAL_API_URL: values.INTERNAL_API_URL ?? defaults.INTERNAL_API_URL,
    TIKTOKEN_CACHE_DIR: values.TIKTOKEN_CACHE_DIR ?? defaults.TIKTOKEN_CACHE_DIR,
  };
}

function serializeEnv(env: DesktopEnv): string {
  const quote = (value: string) =>
    /[\s#"'\\]/.test(value) ? `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"` : value;

  return [
    "# Open Notebook desktop environment (auto-generated on first run)",
    `OPEN_NOTEBOOK_ENCRYPTION_KEY=${env.OPEN_NOTEBOOK_ENCRYPTION_KEY}`,
    `SURREAL_URL=${env.SURREAL_URL}`,
    `SURREAL_USER=${env.SURREAL_USER}`,
    `SURREAL_PASSWORD=${env.SURREAL_PASSWORD}`,
    `SURREAL_NAMESPACE=${env.SURREAL_NAMESPACE}`,
    `SURREAL_DATABASE=${env.SURREAL_DATABASE}`,
    `DATA_FOLDER=${quote(env.DATA_FOLDER)}`,
    `API_HOST=${env.API_HOST}`,
    `API_PORT=${env.API_PORT}`,
    `INTERNAL_API_URL=${env.INTERNAL_API_URL}`,
    `TIKTOKEN_CACHE_DIR=${quote(env.TIKTOKEN_CACHE_DIR)}`,
    "",
  ].join("\n");
}

export function toProcessEnv(desktopEnv: DesktopEnv): NodeJS.ProcessEnv {
  return {
    ...process.env,
    ...desktopEnv,
    API_RELOAD: "false",
  };
}
