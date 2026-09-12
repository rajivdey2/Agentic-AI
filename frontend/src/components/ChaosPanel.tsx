import { AlertTriangle, Clock3, Database, Loader2, MapPin, Scale, TrendingUp, Zap } from "lucide-react";
import type { ReactNode } from "react";
import { WorldState } from "../types";
import { Panel, Pill } from "./Panel";

const TYPES: { type: string; icon: ReactNode; label: string; hint: string; danger: boolean }[] = [
  { type: "vendor_capacity_drop", icon: <Database size={14} />, label: "Vendor capacity drop", hint: "V-CHN capped at 50/day", danger: true },
  { type: "shipment_delay", icon: <Clock3 size={14} />, label: "Shipment delay", hint: "in-flight order delayed 7 days", danger: true },
  { type: "shipment_loss", icon: <AlertTriangle size={14} />, label: "Shipment loss", hint: "an in-transit shipment lost", danger: true },
  { type: "route_closed", icon: <MapPin size={14} />, label: "Route closure", hint: "CHN→MUM lane closed", danger: true },
  { type: "demand_spike", icon: <TrendingUp size={14} />, label: "Demand spike", hint: "order qty jumps + deadline", danger: true },
  { type: "cap_change", icon: <Scale size={14} />, label: "Carbon cap tightened", hint: "carbon cap → 1200", danger: false },
];

export function ChaosPanel(props: {
  state: WorldState;
  busy: boolean;
  onTrigger: (type: string, params: Record<string, unknown>) => Promise<void>;
  onRunAgent: () => Promise<void>;
}) {
  const atRisk = props.state.kpis.at_risk_orders;

  return (
    <Panel title="Chaos & recovery" icon={<Zap size={16} strokeWidth={2} />} tone="default">
      <div className="grid grid-cols-2 gap-2">
        {TYPES.map((t) => (
          <button
            key={t.type}
            type="button"
            disabled={props.busy}
            aria-label={`Fire disruption: ${t.label}`}
            onClick={() => props.onTrigger(t.type, {})}
            title={t.hint}
            className={`rounded-lg border px-2.5 py-2 text-left transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
              t.danger
                ? "border-rose-800/70 bg-rose-950/40 text-rose-200 hover:bg-rose-900/50"
                : "border-amber-800/70 bg-amber-950/40 text-amber-200 hover:bg-amber-900/50"
            }`}
          >
            <span className="flex items-center gap-1.5 text-xs font-semibold">
              <span aria-hidden>{t.icon}</span>
              {t.label}
            </span>
            <span className="mt-0.5 block text-[10px] text-slate-400">{t.hint}</span>
          </button>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={props.onRunAgent}
          disabled={props.busy}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-900/40 transition-colors duration-200 hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
        >
          {props.busy ? (
            <>
              <Loader2 size={15} className="animate-spin" aria-hidden /> Recovering…
            </>
          ) : (
            <>
              <Zap size={15} aria-hidden /> Run recovery agent
            </>
          )}
        </button>
        {atRisk > 0 && (
          <Pill tone="danger" className="animate-pulse">
            <AlertTriangle size={12} aria-hidden /> {atRisk} at risk
          </Pill>
        )}
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
        Fire a live disruption, then run the agent — it replans, executes, and <b className="text-slate-300">really verifies</b> the constraints.
      </p>
    </Panel>
  );
}