import { AlertTriangle, CircleDot, Clock3, Database, FileText, MapPin, Scale, Send, ShoppingCart, TrendingUp, Truck } from "lucide-react";
import type { ReactNode } from "react";
import { EventLogRow } from "../types";
import { Panel, Tone } from "./Panel";

const TYPE_META: Record<string, { icon: ReactNode; tone: Tone; label: string }> = {
  seed: { icon: <Database size={12} />, tone: "default", label: "seed" },
  vendor_capacity_drop: { icon: <Database size={12} />, tone: "danger", label: "vendor capacity drop" },
  shipment_delay: { icon: <Clock3 size={12} />, tone: "danger", label: "shipment delay" },
  shipment_loss: { icon: <AlertTriangle size={12} />, tone: "danger", label: "shipment loss" },
  route_closed: { icon: <MapPin size={12} />, tone: "danger", label: "route closed" },
  demand_spike: { icon: <TrendingUp size={12} />, tone: "warning", label: "demand spike" },
  cap_change: { icon: <Scale size={12} />, tone: "warning", label: "cap change" },
  reroute_shipment: { icon: <Send size={12} />, tone: "info", label: "reroute" },
  place_order: { icon: <ShoppingCart size={12} />, tone: "success", label: "place order" },
  allocate_inventory: { icon: <Database size={12} />, tone: "success", label: "allocate" },
  transfer_stock: { icon: <Truck size={12} />, tone: "info", label: "transfer" },
  shipment_cancel: { icon: <CircleDot size={12} />, tone: "default", label: "cancel" },
};

export function EventLog(props: { events: EventLogRow[]; lastSeq: number }) {
  const rows = [...props.events].sort((a, b) => b.seq - a.seq);

  return (
    <Panel
      title={`Audit trail · ${rows.length} events`}
      icon={<FileText size={16} strokeWidth={2} />}
      right={
        <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" aria-hidden />
          append-only
        </span>
      }
    >
      <div className="max-h-80 space-y-1 overflow-y-auto pr-1" role="log" aria-label="Event audit trail">
        {rows.map((e) => {
          const meta = TYPE_META[e.type] ?? { icon: <CircleDot size={12} />, tone: "default" as Tone, label: e.type };
          return (
            <div key={e.seq} className="flex items-start gap-2 rounded-lg bg-slate-950/40 px-2 py-1.5">
              <span className="w-7 shrink-0 text-right tnum text-[10px] text-slate-600">#{e.seq}</span>
              <span className="tnum shrink-0 text-[10px] text-slate-600">d{e.day}</span>
              <span
                aria-hidden
                className="mt-[1px] shrink-0 rounded border border-slate-800 p-[3px] text-slate-400"
              >
                {meta.icon}
              </span>
              <span className="text-[13px] leading-snug text-slate-300">
                <b className="font-medium text-slate-200">{meta.label}</b>{" "}
                <span className="text-slate-500">{describe(e)}</span>
              </span>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function describe(e: EventLogRow): string {
  const p = e.payload;
  switch (e.type) {
    case "seed":
      return `${Object.keys(p.orders ?? {}).length} orders, ${Object.keys(p.shipments ?? {}).length} shipments`;
    case "vendor_capacity_drop":
      return `${p.vendor_id} → ${p.new_capacity}/day`;
    case "shipment_delay":
      return `${p.shipment_id} +${p.delay_days}d`;
    case "shipment_loss":
      return p.shipment_id;
    case "route_closed":
      return p.route_id;
    case "demand_spike":
      return `${p.order_id} → ${p.new_qty} units`;
    case "cap_change":
      return `carbon cap → ${p.carbon_cap}`;
    case "reroute_shipment":
      return `${p.shipment_id} → ${p.route_id}`;
    case "place_order":
      return `${p.qty}×${p.order_id} · ${p.vendor_id} · ${p.route_id}`;
    case "allocate_inventory":
      return `${p.qty}×${p.order_id} · ${p.warehouse_id} · ${p.route_id}`;
    case "transfer_stock":
      return `${p.qty} ${p.sku} ${p.from_wh} → ${p.to_wh}`;
    case "shipment_cancel":
      return p.shipment_id;
    default:
      return "";
  }
}