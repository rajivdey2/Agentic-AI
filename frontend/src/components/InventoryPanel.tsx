import { Database } from "lucide-react";
import { WorldState } from "../types";
import { Panel, Pill } from "./Panel";

interface Vendor {
  id: string;
  name: string;
  location: string;
  reliability: number;
  capacity: number;
  capacity_used: Record<string, number>;
}

export function InventoryPanel(props: { state: WorldState; className?: string }) {
  const whs = Object.keys(props.state.inventory);
  const skus = Object.keys(props.state.skus);
  const vendors = Object.values(props.state.vendors) as Vendor[];

  return (
    <Panel title="Inventory & capacity" icon={<Database size={16} strokeWidth={2} />} className={props.className}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
              <th className="py-1 pr-2 font-medium">Warehouse</th>
              {skus.map((s) => (
                <th key={s} className="py-1 pr-2 text-right font-medium">
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {whs.map((wh) => (
              <tr key={wh} className="border-t border-slate-800/70 transition-colors hover:bg-slate-800/40">
                <td className="py-2 pr-2 font-medium text-slate-200">{wh}</td>
                {skus.map((s) => {
                  const q = props.state.inventory[wh]?.[s] ?? 0;
                  return (
                    <td key={s} className={`py-2 pr-2 text-right tnum ${q === 0 ? "text-slate-600" : "text-slate-300"}`}>
                      {q}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-5">
        {vendors.map((v) => {
          const used = Object.values(v.capacity_used ?? {}).reduce((a: number, b: number) => a + b, 0);
          const over = used > v.capacity;
          const pct = Math.min(100, (used / Math.max(1, v.capacity)) * 100);
          return (
            <div
              key={v.id}
              className="rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2"
              title={`${v.name} · ${v.location}`}
            >
              <div className="flex items-center justify-between gap-1">
                <span className="truncate text-xs font-semibold text-slate-200">{v.name}</span>
                <span className={`tnum text-[11px] ${over ? "text-rose-400" : pct >= 85 ? "text-amber-400" : "text-slate-500"}`}>
                  {used}/{v.capacity}
                </span>
              </div>
              <div className="capbar mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800" aria-hidden>
                <span
                  className={`block h-full rounded-full ${over ? "bg-rose-500" : pct >= 85 ? "bg-amber-500" : "bg-emerald-600"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px] text-slate-500">
                <span>{v.location} · rel {v.reliability.toFixed(2)}</span>
                {over && <Pill tone="danger">over</Pill>}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}