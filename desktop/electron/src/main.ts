import { app, BrowserWindow, dialog } from "electron";
import path from "path";

import { loadOrCreateDesktopEnv } from "./env-manager";
import { ensureDataDirs, resolveDesktopPaths } from "./paths";
import { ProcessManager } from "./process-manager";

let splashWindow: BrowserWindow | null = null;
let mainWindow: BrowserWindow | null = null;
let processManager: ProcessManager | null = null;

const gotSingleInstanceLock = app.requestSingleInstanceLock();

if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    try {
      await bootstrapApplication();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      await dialog.showErrorBox("Open Notebook failed to start", message);
      app.quit();
    }
  });

  app.on("window-all-closed", () => {
    app.quit();
  });

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      try {
        await bootstrapApplication();
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        await dialog.showErrorBox("Open Notebook failed to start", message);
        app.quit();
      }
    }
  });

  app.on("before-quit", (event) => {
    if (!processManager) {
      return;
    }
    event.preventDefault();
    void shutdownAndQuit();
  });
}

async function bootstrapApplication(): Promise<void> {
  const paths = resolveDesktopPaths();
  ensureDataDirs(paths);

  const desktopEnv = loadOrCreateDesktopEnv(
    paths.desktopEnvFile,
    paths.dataFolder,
    paths.repoRoot,
    paths.isDev
  );

  createSplashWindow();
  setStartupStatus("Preparing services…");

  processManager = new ProcessManager(paths, desktopEnv, setStartupStatus);
  await processManager.start();

  setStartupStatus("Opening Open Notebook…");
  createMainWindow(paths.uiUrl, paths.isDev);
  splashWindow?.close();
  splashWindow = null;
}

async function shutdownAndQuit(): Promise<void> {
  setStartupStatus("Shutting down…");
  if (processManager) {
    await processManager.stop();
    processManager = null;
  }
  app.exit(0);
}

function createSplashWindow(): void {
  splashWindow = new BrowserWindow({
    width: 420,
    height: 260,
    frame: false,
    resizable: false,
    center: true,
    show: true,
    alwaysOnTop: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  void splashWindow.loadFile(path.join(__dirname, "..", "splash.html"));
}

function createMainWindow(uiUrl: string, isDev: boolean): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    show: false,
    title: "Open Notebook",
    backgroundColor: "#0f172a",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });

  mainWindow.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription, validatedURL) => {
      console.error(
        `[electron] Failed to load ${validatedURL}: ${errorCode} ${errorDescription}`
      );
    }
  );

  void mainWindow.loadURL(uiUrl);

  if (isDev || process.env.OPEN_NOTEBOOK_ELECTRON_DEVTOOLS === "1") {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function setStartupStatus(message: string): void {
  splashWindow?.webContents.send("startup-status", message);
}
