import { Activity, AlertTriangle, Database, FileText, Gauge, Send, ShieldCheck, Zap } from "lucide-react";
import type { ReactNode } from "react";
import { AgentTrace } from "../types";
import { Panel, Pill, Tone } from "./Panel";

const STEP_META: Record<string, { icon: ReactNode; tone: Tone; label: string }> = {
  monitor: { icon: <Activity size={13} />, tone: "default", label: "monitor" },
  detect: { icon: <AlertTriangle size={13} />, tone: "danger", label: "detect" },
  retrieve: { icon: <Database size={13} />, tone: "info", label: "retrieve" },
  optimize: { icon: <Gauge size={13} />, tone: "warning", label: "optimize" },
  decide: { icon: <FileText size={13} />, tone: "info", label: "decide" },
  execute: { icon: <Send size={13} />, tone: "success", label: "execute" },
  verify: { icon: <ShieldCheck size={13} />, tone: "success", label: "verify" },
  escalate_to_human: { icon: <Zap size={13} />, tone: "danger", label: "escalate" },
};

export function TracePanel(props: { trace: AgentTrace | null }) {
  return (
    <Panel
      title="Decision trace"
      icon={<Gauge size={16} strokeWidth={2} />}
      right={props.trace ? <span className="tnum text-[11px] text-slate-500">{props.trace.run_id}</span> : undefined}
    >
      {!props.trace ? (
        <p className="text-sm leading-relaxed text-slate-500">
          Run the recovery agent (Chaos panel) to capture the state-graph trace with real verification results.
        </p>
      ) : (
        <TraceTimeline trace={props.trace} />
      )}
    </Panel>
  );
}

function TraceTimeline(props: { trace: AgentTrace }) {
  const lastVerify = [...props.trace.trace].reverse().find((t) => t.step === "verify");
  const decision = props.trace.decision;

  return (
    <div>
      {decision?.justification && (
        <blockquote className="mb-3 rounded-lg border-l-2 border-sky-500 bg-sky-950/30 p-3">
          <p className="text-[13px] leading-relaxed text-slate-200">{decision.justification}</p>
          {decision.provider && (
            <div className="mt-1.5 flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
              <Pill tone="info">{decision.provider}</Pill>
              {typeof decision.latency_ms === "number" && <span className="tnum">{decision.latency_ms}ms</span>}
            </div>
          )}
        </blockquote>
      )}

      <ol className="relative space-y-2 before:absolute before:left-[13px] before:top-2 before:bottom-2 before:w-px before:bg-slate-800">
        {props.trace.trace.map((t, i) => {
          const meta = STEP_META[t.step] ?? { icon: <Activity size={13} />, tone: "default" as Tone, label: t.step };
          const passed = typeof t.passed === "boolean";
          return (
            <li key={i} className="relative flex items-start gap-3">
              <span
                aria-hidden
                className={`z-10 mt-0.5 flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full border ${iconRing(meta.tone)} ${iconBg(meta.tone)}`}
              >
                {meta.icon}
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-semibold uppercase tracking-widest text-slate-300">{meta.label}</span>
                  <span className="tnum text-[10px] text-slate-600">d{t.day ?? "?"}</span>
                  {passed && (
                    <Pill tone={t.passed ? "success" : "danger"}>
                      {t.passed ? "PASS" : "FAIL"}
                    </Pill>
                  )}
                </div>
                <p className="text-[12.5px] leading-snug text-slate-400">{t.summary}</p>
                {t.choice && (
                  <code className="mt-1 inline-block max-w-full truncate rounded bg-slate-950/70 px-1.5 py-0.5 tnum text-[10.5px] text-cyan-300">
                    {t.choice}
                  </code>
                )}
                {t.issues_after && t.issues_after.length > 0 && (
                  <p className="mt-1 text-[11px] text-rose-400">issues: {t.issues_after.join(", ")}</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {lastVerify && (
        <div
          className={`mt-3 rounded-lg border px-3 py-2 text-sm font-medium ${
            lastVerify.passed ? "border-emerald-800/70 bg-emerald-950/30 text-emerald-300" : "border-rose-800/70 bg-rose-950/30 text-rose-300"
          }`}
          role="status"
        >
          {lastVerify.passed ? "✓ Constraints satisfied after replan" : "✗ Constraints still violated — escalated"}
        </div>
      )}
    </div>
  );
}

function iconRing(tone: Tone) {
  switch (tone) {
    case "danger":
      return "border-rose-800";
    case "success":
      return "border-emerald-800";
    case "warning":
      return "border-amber-800";
    case "info":
      return "border-sky-800";
    default:
      return "border-slate-700";
  }
}

function iconBg(tone: Tone) {
  switch (tone) {
    case "danger":
      return "bg-rose-950/60 text-rose-300";
    case "success":
      return "bg-emerald-950/60 text-emerald-300";
    case "warning":
      return "bg-amber-950/60 text-amber-300";
    case "info":
      return "bg-sky-950/60 text-sky-300";
    default:
      return "bg-slate-800/70 text-slate-300";
  }
}