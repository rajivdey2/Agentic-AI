import type { AgentTrace, WorldState, EventLogRow } from "./types";

const BASE = "/api";

async function j<T>(p: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${p}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  state: () => j<WorldState>("/state"),
  events: (after = 0) => j<EventLogRow[]>(`/events?after=${after}`),
  disruptionTypes: () => j<{ types: string[] }>("/disruptions/types"),
  trigger: (type: string, params: Record<string, unknown> = {}) =>
    j<any>("/disruptions/trigger", { method: "POST", body: JSON.stringify({ type, params }) }),
  runAgent: () => j<any>("/agent/run", { method: "POST" }),
  trace: (id: string) => j<AgentTrace>(`/agent/trace/${id}`),
  candidates: (orderId?: string) => j<any>(`/candidates${orderId ? `?order_id=${orderId}` : ""}`),
  reset: () => j<any>("/reset", { method: "POST" }),
};