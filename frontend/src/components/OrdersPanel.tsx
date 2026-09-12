import { AlertTriangle, ShoppingCart } from "lucide-react";
import { WorldState } from "../types";
import { Dot, Panel, Pill, Tone } from "./Panel";

const SKU_COLORS = ["text-sky-400", "text-violet-400", "text-amber-400"];

export function OrdersPanel(props: { state: WorldState; className?: string }) {
  const orders = Object.values(props.state.orders);
  const riskIds = new Set(props.state.risk_orders.map((r) => r.order_id));

  return (
    <Panel
      title="Orders"
      icon={<ShoppingCart size={16} strokeWidth={2} />}
      right={
        riskIds.size > 0 ? (
          <Pill tone="danger">
            <AlertTriangle size={12} aria-hidden /> {riskIds.size} at risk
          </Pill>
        ) : (
          <Pill tone="success">all covered</Pill>
        )
      }
      className={props.className}
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
              <th className="py-1 pr-2 font-medium">Order</th>
              <th className="py-1 pr-2 font-medium">SKU</th>
              <th className="py-1 pr-2 text-right font-medium">Qty</th>
              <th className="py-1 pr-2 text-right font-medium">Deadline</th>
              <th className="py-1 pr-2 text-right font-medium">Shortfall</th>
              <th className="py-1 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o, i) => {
              const risk = riskIds.has(o.id);
              const tone: Tone = risk ? "danger" : o.status === "fulfilled" ? "success" : "default";
              return (
                <tr
                  key={o.id}
                  className={`border-t border-slate-800/70 transition-colors ${risk ? "bg-rose-950/40" : "hover:bg-slate-800/40"}`}
                >
                  <td className="py-2 pr-2 font-semibold text-slate-100">
                    <span className="inline-flex min-w-[3.25rem] items-center gap-2">
                      {risk && <AlertTriangle size={13} className="text-rose-400" aria-label="at risk" />}
                      {o.id}
                    </span>
                  </td>
                  <td className={`py-2 pr-2 font-medium ${SKU_COLORS[i % SKU_COLORS.length]}`}>{o.sku}</td>
                  <td className="py-2 pr-2 text-right tnum">{o.qty}</td>
                  <td className="py-2 pr-2 text-right tnum text-slate-300">d{o.deadline}</td>
                  <td className="py-2 pr-2 text-right tnum">
                    {o.shortfall > 0 ? <b className="text-rose-300">{o.shortfall}</b> : <span className="text-slate-600">–</span>}
                  </td>
                  <td className="py-2 text-right">
                    <Pill tone={tone}>
                      <Dot tone={tone} /> {o.status}
                    </Pill>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}