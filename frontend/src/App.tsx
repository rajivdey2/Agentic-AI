import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { api } from "./api";
import type { AgentTrace, EventLogRow, WorldState } from "./types";
import { KpisPanel } from "./components/KpisPanel";
import { OrdersPanel } from "./components/OrdersPanel";
import { ShipmentsPanel } from "./components/ShipmentsPanel";
import { InventoryPanel } from "./components/InventoryPanel";
import { TracePanel } from "./components/TracePanel";
import { ChaosPanel } from "./components/ChaosPanel";
import { EventLog } from "./components/EventLog";

const POLL_MS = 2500;

export default function App() {
  const [state, setState] = useState<WorldState | null>(null);
  const [events, setEvents] = useState<EventLogRow[]>([]);
  const [lastEventSeq, setLastEventSeq] = useState(0);
  const [trace, setTrace] = useState<AgentTrace | null>(null);
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [toast, setToast] = useState<{ text: string; tone: "ok" | "err" } | null>(null);
  const toastTimer = useRef<number | undefined>(undefined);

  const refresh = useCallback(async () => {
    const [st, ev] = await Promise.all([api.state(), api.events()]);
    setState(st);
    setEvents(ev);
    if (ev.length > 0) setLastEventSeq(ev[ev.length - 1].seq);
    setOnline(true);
    setLastSync(new Date());
  }, []);

  useEffect(() => {
    let stopped = false;
    refresh().catch(() => stopped || setOnline(false));
    const id = setInterval(() => {
      refresh().catch(() => {
        if (!stopped) setOnline(false);
      });
    }, POLL_MS);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, [refresh]);

  const flash = (text: string, tone: "ok" | "err" = "ok") => {
    setToast({ text, tone });
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 4200);
  };

  const trigger = async (type: string, params: Record<string, unknown> = {}) => {
    setBusy(true);
    try {
      const res = await api.trigger(type, params);
      flash(`Disruption fired: ${res.label}`);
      await refresh();
    } catch (e) {
      flash(`Disruption failed: ${e}`, "err");
    } finally {
      setBusy(false);
    }
  };

  const runAgent = async () => {
    setBusy(true);
    try {
      const result = await api.runAgent();
      const thread = result.run_id;
      setTrace(await api.trace(thread));
      const ok = result.verification?.passed;
      flash(`Agent run complete · verification ${ok ? "PASSED" : "FAILED → escalated"}`, ok ? "ok" : "err");
      await refresh();
    } catch (e) {
      flash(`Agent run failed: ${e}`, "err");
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    setBusy(true);
    try {
      await api.reset();
      setTrace(null);
      flash("World reset to baseline");
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Header
        state={state}
        online={online}
        lastSync={lastSync}
        busy={busy}
        onRefresh={refresh}
        onReset={reset}
      />

      {toast && <Toast text={toast.text} tone={toast.tone} />}

      <main className="mx-auto max-w-[1440px] px-4 pb-8 pt-4 lg:px-6">
        {!state ? (
          <SkeletonScreen />
        ) : (
          <div className="grid grid-cols-12 items-start gap-4">
            <div className="col-span-12 flex min-w-0 flex-col gap-4 lg:col-span-8">
              <KpisPanel state={state} />
              <OrdersPanel state={state} />
              <ShipmentsPanel state={state} />
              <InventoryPanel state={state} />
            </div>
            <div className="col-span-12 flex min-w-0 flex-col gap-4 lg:col-span-4">
              <ChaosPanel state={state} busy={busy} onTrigger={trigger} onRunAgent={runAgent} />
              <TracePanel trace={trace} />
              <EventLog events={events} lastSeq={lastEventSeq} />
            </div>
          </div>
        )}

        <footer className="mt-6 border-t border-slate-800/70 pt-3 text-center text-[11px] text-slate-600">
          Event-sourced SimWorld · OR-Tools CP-SAT · LangGraph agent · FastAPI — Tech Zephyr 4.0, Track 3 / PS6
        </footer>
      </main>
    </div>
  );
}

function Header(props: {
  state: WorldState | null;
  online: boolean;
  lastSync: Date | null;
  busy: boolean;
  onRefresh: () => void;
  onReset: () => void;
}) {
  const atRisk = props.state?.kpis.at_risk_orders ?? 0;
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-[1440px] items-center gap-4 px-4 py-3 lg:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600/15 text-emerald-400 ring-1 ring-emerald-700/50">
            <Activity size={18} strokeWidth={2.4} aria-hidden />
          </span>
          <div>
            <h1 className="text-[15px] font-bold leading-tight tracking-tight">
              Autonomous Retail Supply Chain <span className="text-emerald-400">Recovery Agent</span>
            </h1>
            <p className="text-[11px] text-slate-500">Tech Zephyr 4.0 · Track 3 · PS6 · FastAPI + LangGraph + OR-Tools</p>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden items-center gap-1.5 rounded-full border border-slate-800 px-3 py-1 text-[11px] text-slate-400 sm:inline-flex">
            <span
              aria-hidden
              className={`h-1.5 w-1.5 rounded-full ${props.online ? "bg-emerald-500" : "bg-rose-500"}`}
            />
            {props.online ? "live" : "offline"}
            {props.lastSync && <span className="tnum text-slate-600">· {props.lastSync.toLocaleTimeString()}</span>}
          </span>

          <span className="rounded-full border border-slate-800 px-3 py-1 text-[11px] text-slate-300">
            Sim day <b className="tnum text-amber-300">{props.state?.day ?? "–"}</b>
          </span>

          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-medium ${
              atRisk > 0 ? "border border-rose-800/70 bg-rose-950 text-rose-300" : "border border-emerald-800/70 bg-emerald-950 text-emerald-300"
            }`}
          >
            {atRisk > 0 ? (
              <>
                <AlertTriangle size={12} aria-hidden /> {atRisk} at risk
              </>
            ) : (
              <>
                <ShieldCheck size={12} aria-hidden /> Objectives met
              </>
            )}
          </span>

          <button
            type="button"
            onClick={props.onRefresh}
            title="Refresh now"
            aria-label="Refresh state"
            disabled={props.busy}
            className="rounded-lg border border-slate-800 p-2 text-slate-400 transition-colors duration-200 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-40"
          >
            <RefreshCw size={14} className={props.busy ? "animate-spin" : ""} aria-hidden />
          </button>
          <button
            type="button"
            onClick={props.onReset}
            title="Reset world to baseline"
            aria-label="Reset world to baseline"
            disabled={props.busy}
            className="rounded-lg border border-slate-800 p-2 text-slate-400 transition-colors duration-200 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-40"
          >
            <RotateCcw size={14} aria-hidden />
          </button>
        </div>
      </div>
    </header>
  );
}

function Toast(props: { text: string; tone: "ok" | "err" }) {
  const ok = props.tone === "ok";
  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-4 right-4 z-30 flex max-w-md items-center gap-2 rounded-lg border px-3 py-2.5 text-sm shadow-xl ${
        ok ? "border-emerald-800/70 bg-slate-900 text-emerald-300" : "border-rose-800/70 bg-slate-900 text-rose-300"
      }`}
    >
      {ok ? <CheckCircle2 size={16} aria-hidden /> : <AlertTriangle size={16} aria-hidden />}
      <span className="truncate">{props.text}</span>
    </div>
  );
}

function SkeletonScreen() {
  return (
    <div className="grid grid-cols-12 gap-4" aria-hidden>
      <div className="col-span-12 skeleton lg:col-span-8">
        <div className="h-20 rounded-xl bg-slate-900/70" />
        <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-slate-900/70" />
          ))}
        </div>
      </div>
      <div className="col-span-12 flex flex-col gap-4 lg:col-span-4">
        <div className="h-52 animate-pulse rounded-xl bg-slate-900/70" />
        <div className="h-64 animate-pulse rounded-xl bg-slate-900/70" />
      </div>
    </div>
  );
}