import { Activity, ShieldCheck, ShieldAlert, Scale, BadgeIndianRupee } from "lucide-react";
import type { ReactNode } from "react";
import { Panel, Pill, Tone } from "./Panel";

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function fmtINR(n: number): string {
  return `${n < 0 ? "-" : ""}₹${inr.format(Math.abs(n))}`;
}

export function KpisPanel(props: { state: WorldStateLike; className?: string }) {
  const k = props.state.kpis;
  const target = props.state.objectives?.on_time_target ?? 0.95;
  const onTime = k.on_time_rate * 100;
  const ok = k.on_time_rate >= target;
  const budgetOver = k.total_cost > k.budget_cap;
  const carbonOver = k.total_carbon > k.carbon_cap;

  return (
    <Panel
      title="Performance against objectives"
      icon={<Activity size={16} strokeWidth={2} />}
      right={
        ok && !budgetOver && !carbonOver ? (
          <Pill tone="success">
            <ShieldCheck size={12} aria-hidden /> On track
          </Pill>
        ) : (
          <Pill tone="danger">
            <ShieldAlert size={12} aria-hidden /> Attention needed
          </Pill>
        )
      }
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label={`On-time SLA · target ${Math.round(target * 100)}%`}>
          <Ring value={onTime} danger={!ok}>
            <div className="text-center leading-none">
              <div className={`text-3xl font-bold tnum ${ok ? "text-emerald-400" : "text-rose-400"}`}>
                {onTime.toFixed(1)}%
              </div>
              <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">delivery</div>
            </div>
          </Ring>
        </StatCard>

        <StatCard label="Committed cost · budget cap">
          <CapBar
            icon={<BadgeIndianRupee size={14} aria-hidden />}
            value={k.total_cost}
            cap={k.budget_cap}
            fmt={(n) => fmtINR(n)}
            over={budgetOver}
            headroom={k.remaining_budget}
          />
        </StatCard>

        <StatCard label="Committed carbon · carbon cap">
          <CapBar
            icon={<Scale size={14} aria-hidden />}
            value={k.total_carbon}
            cap={k.carbon_cap}
            fmt={(n) => `${Math.round(n).toLocaleString("en-IN")} kg`}
            over={carbonOver}
            headroom={k.remaining_carbon}
          />
        </StatCard>

        <StatCard label="Orders · fulfilment outlook">
          <div className="flex h-full flex-col justify-center gap-1.5 text-sm">
            <Row label="Open orders" value={String(k.open_orders)} />
            <Row label="Delivered on time" value={String(k.on_time_delivered)} tone={ok ? "success" : "default"} />
            <Row
              label="At risk"
              value={String(k.at_risk_orders)}
              tone={k.at_risk_orders > 0 ? "danger" : "success"}
            />
          </div>
        </StatCard>
      </div>
    </Panel>
  );
}

function StatCard(props: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
      <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-500">{props.label}</div>
      {props.children}
    </div>
  );
}

function Row(props: { label: string; value: string; tone?: Tone }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400">{props.label}</span>
      <b className={`font-semibold tnum ${props.tone === "danger" ? "text-rose-400" : props.tone === "success" ? "text-emerald-400" : "text-slate-100"}`}>
        {props.value}
      </b>
    </div>
  );
}

function Ring(props: { value: number; danger: boolean; children: ReactNode }) {
  const color = props.danger ? "#fb7185" : "#34d399";
  const pct = Math.min(100, Math.max(0, props.value));
  return (
    <div
      role="img"
      aria-label={`On-time delivery ${props.value.toFixed(1)} percent`}
      className="relative mx-auto h-28 w-28 rounded-full"
      style={{
        background: `conic-gradient(${color} ${pct * 3.6}deg, rgba(30,41,59,0.6) 0deg)`,
      }}
    >
      <div className="absolute inset-2 flex items-center justify-center rounded-full bg-slate-950">{props.children}</div>
    </div>
  );
}

function CapBar(props: {
  icon: ReactNode;
  value: number;
  cap: number;
  fmt: (n: number) => string;
  over: boolean;
  headroom: number;
}) {
  const pct = Math.min(100, (props.value / props.cap) * 100);
  return (
    <div className="flex h-full flex-col justify-center gap-1.5">
      <div className="flex items-baseline justify-between">
        <span className="text-xl font-bold tnum text-slate-100">{props.fmt(props.value)}</span>
        <span className="text-[11px] text-slate-500 tnum">of {props.fmt(props.cap)}</span>
      </div>
      <div className="capbar h-2 w-full overflow-hidden rounded-full bg-slate-800" aria-hidden>
        <span
          className={`block h-full rounded-full ${props.over ? "bg-rose-500" : "bg-gradient-to-r from-emerald-600 to-emerald-400"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center gap-1 text-[11px]">
        <span aria-hidden>{props.icon}</span>
        <span className={props.over ? "font-semibold text-rose-400" : "text-slate-400"}>
          {props.over
            ? `over cap by ${props.fmt(Math.abs(props.headroom))}`
            : `${props.fmt(props.headroom)} headroom`}
        </span>
      </div>
    </div>
  );
}

// Minimal structural typing — mirrors backend contract in ./types.ts
interface WorldStateLike {
  kpis: {
    on_time_rate: number;
    total_cost: number;
    total_carbon: number;
    budget_cap: number;
    carbon_cap: number;
    remaining_budget: number;
    remaining_carbon: number;
    open_orders: number;
    on_time_delivered: number;
    at_risk_orders: number;
  };
  objectives?: { on_time_target?: number };
}