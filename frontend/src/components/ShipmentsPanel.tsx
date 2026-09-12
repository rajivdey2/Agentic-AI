import { Truck } from "lucide-react";
import { Shipment, WorldState } from "../types";
import { Dot, Panel, Pill, Tone } from "./Panel";

export function ShipmentsPanel(props: { state: WorldState; className?: string }) {
  const ships = Object.values(props.state.shipments).sort((a, b) => a.eta - b.eta);
  const day = props.state.day ?? 0;

  return (
    <Panel
      title="In-flight shipments"
      icon={<Truck size={16} strokeWidth={2} />}
      right={<span className="tnum text-slate-500">{ships.length}</span>}
      className={props.className}
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
              <th className="py-1 pr-2 font-medium">ID</th>
              <th className="py-1 pr-2 font-medium">Lane</th>
              <th className="py-1 pr-2 text-right font-medium">Qty</th>
              <th className="py-1 pr-2 text-right font-medium">ETA</th>
              <th className="py-1 pr-2 text-right font-medium">Cost</th>
              <th className="py-1 pr-2 text-right font-medium">Carbon</th>
              <th className="py-1 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {ships.map((s: Shipment) => {
              const statusTone = statusToneOf(s.status);
              const late = s.status === "in_transit" && s.eta <= day;
              return (
                <tr key={s.id} className="border-t border-slate-800/70 transition-colors hover:bg-slate-800/40">
                  <td className="py-2 pr-2 font-semibold text-slate-100">{s.id}</td>
                  <td className="py-2 pr-2 text-xs text-slate-300">
                    <span className="font-medium text-slate-200">{s.origin}</span>
                    <span className="mx-1 text-slate-600">→</span>
                    <span className="font-medium text-slate-200">{s.dest}</span>
                    <span className="mx-1 tnum text-slate-500">· {s.route_id}</span>
                  </td>
                  <td className="py-2 pr-2 text-right tnum">
                    {s.qty} <span className="text-[11px] text-slate-500">{s.sku}</span>
                  </td>
                  <td className="py-2 pr-2 text-right tnum">
                    <span className={late ? "font-semibold text-rose-400" : "text-slate-300"}>d{s.eta}</span>
                    {s.status === "in_transit" && <span className="ml-1 text-[11px] text-slate-500">T-{Math.max(0, s.eta - day)}</span>}
                  </td>
                  <td className="py-2 pr-2 text-right tnum text-slate-300">{s.cost.toLocaleString("en-IN")}</td>
                  <td className="py-2 pr-2 text-right tnum text-slate-300">{s.carbon.toLocaleString("en-IN")}kg</td>
                  <td className="py-2 text-right">
                    <Pill tone={statusTone}>
                      <Dot tone={statusTone} /> {s.status.replace("_", " ")}
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

function statusToneOf(status: string): Tone {
  switch (status) {
    case "delivered":
      return "success";
    case "lost":
      return "danger";
    case "cancelled":
      return "default";
    default:
      return "info";
  }
}