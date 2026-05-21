import type { StartTaskMessage, TaskContext, HandlerResult } from '@blocks-network/sdk';
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export default async function handler(
  task: StartTaskMessage,
  ctx?: TaskContext,
): Promise<HandlerResult> {
  const input = task.requestParts?.[0] as Record<string, unknown> | undefined;
  const request = parseRequest(input);

  ctx?.reportStatus(`Broker MCP tool: ${request.tool ?? 'unknown'}`);
  let result: unknown;
  try {
    result = await runBroker(request);
  } catch (error) {
    result = {
      ok: false,
      request_id: request.request_id,
      error: errorMessage(error),
      fallback: 'Run blocks_mcp_broker.py directly with the same MCP-style request envelope.',
    };
  }

  return {
    artifacts: [
      {
        data: JSON.stringify(result, null, 2),
        mimeType: 'application/json',
        outputId: 'result',
      },
    ],
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function parseRequest(input: Record<string, unknown> | undefined): Record<string, unknown> {
  const raw = input?.text ?? input?.request ?? input;
  if (typeof raw === 'string') {
    return JSON.parse(raw) as Record<string, unknown>;
  }
  if (raw && typeof raw === 'object') {
    return raw as Record<string, unknown>;
  }
  throw new Error('Expected a JSON MCP broker request');
}

function runBroker(request: Record<string, unknown>): Promise<unknown> {
  const agentDir = dirname(fileURLToPath(import.meta.url));
  const repoRoot = resolve(agentDir, '..');
  const script = resolve(repoRoot, 'blocks_mcp_broker.py');

  return new Promise((resolvePromise, reject) => {
    const child = spawn(process.env.PYTHON_BIN ?? 'python3.11', [script], {
      cwd: repoRoot,
      env: { ...process.env },
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `blocks_mcp_broker.py exited with ${code}`));
        return;
      }
      try {
        resolvePromise(JSON.parse(stdout));
      } catch (error) {
        reject(new Error(`Invalid JSON from blocks_mcp_broker.py: ${stdout}`));
      }
    });

    child.stdin.write(JSON.stringify(request));
    child.stdin.end();
  });
}
