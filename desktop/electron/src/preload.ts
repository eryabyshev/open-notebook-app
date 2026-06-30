import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("desktop", {
  onStatus(callback: (message: string) => void): void {
    ipcRenderer.on("startup-status", (_event, message: string) => {
      callback(message);
    });
  },
});

declare global {
  interface Window {
    desktop?: {
      onStatus: (callback: (message: string) => void) => void;
    };
  }
}

export {};
