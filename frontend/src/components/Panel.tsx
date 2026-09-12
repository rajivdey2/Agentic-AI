import type { ReactNode } from "react";

export type Tone = "default" | "danger" | "success" | "info" | "warning";

const STRIPE: Record<Tone, string> = {
  default: "bg-slate-700",
  danger: "bg-rose-500",
  success: "bg-emerald-500",
  info: "bg-sky-500",
  warning: "bg-amber-500",
};

const BORDER: Record<Tone, string> = {
  default: "border-slate-800",
  danger: "border-rose-900/80",
  success: "border-emerald-900/80",
  info: "border-sky-900/80",
  warning: "border-amber-900/80",
};

export function Panel(props: {
  title: string;
  icon?: ReactNode;
  right?: ReactNode;
  tone?: Tone;
  className?: string;
  children?: ReactNode;
}) {
  const tone = props.tone ?? "default";
  return (
    <section
      className={`relative rounded-xl border ${BORDER[tone]} bg-slate-900/60 backdrop-blur p-4 shadow-lg shadow-black/20 ${props.className ?? ""}`}
    >
      <span aria-hidden className={`absolute left-0 top-5 bottom-5 w-[3px] rounded-full ${STRIPE[tone]}`} />
      <header className="flex items-center gap-2 pl-2 mb-3">
        {props.icon && <span className="shrink-0 text-slate-400" aria-hidden>{props.icon}</span>}
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">{props.title}</h2>
        {props.right && <span className="ml-auto shrink-0">{props.right}</span>}
      </header>
      {props.children}
    </section>
  );
}

export function Pill(props: { tone: Tone; children: ReactNode; className?: string }) {
  const tone = props.tone ?? "default";
  const colors: Record<Tone, string> = {
    default: "bg-slate-800 text-slate-300",
    danger: "bg-rose-950 text-rose-300 border border-rose-800/70",
    success: "bg-emerald-950 text-emerald-300 border border-emerald-800/70",
    info: "bg-sky-950 text-sky-300 border border-sky-800/70",
    warning: "bg-amber-950 text-amber-300 border border-amber-800/70",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${colors[tone]} ${props.className ?? ""}`}>
      {props.children}
    </span>
  );
}

export function Dot(props: { tone: Tone }) {
  const tone = props.tone ?? "default";
  const c: Record<Tone, string> = {
    default: "bg-slate-400",
    danger: "bg-rose-500",
    success: "bg-emerald-500",
    info: "bg-sky-500",
    warning: "bg-amber-500",
  };
  return <span aria-hidden className={`inline-block h-1.5 w-1.5 rounded-full ${c[tone]}`} />;
}