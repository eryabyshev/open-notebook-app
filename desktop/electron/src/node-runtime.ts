export interface NodeRuntime {
  command: string;
  argsPrefix: string[];
  extraEnv: Record<string, string>;
}

/**
 * Run Next.js standalone server.js with Node.
 * Always use Electron's binary as Node — reliable PATH in GUI/subprocess spawns.
 */
export function resolveNodeRuntime(): NodeRuntime {
  return {
    command: process.execPath,
    argsPrefix: [],
    extraEnv: { ELECTRON_RUN_AS_NODE: "1" },
  };
}
