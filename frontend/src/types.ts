// Typed mirror of the backend JSON contract.

export interface Kpis {
  total_cost: number;
  total_carbon: number;
  on_time_delivered: number;
  orders_fulfilled: number;
  on_time_rate: number;
  budget_cap: number;
  carbon_cap: number;
  remaining_budget: number;
  remaining_carbon: number;
  open_orders: number;
  at_risk_orders: number;
}

export interface Issues {
  kind: string;
  detail?: string;
}

export interface Order {
  id: string;
  sku: string;
  qty: number;
  dest: string;
  deadline: number;
  status: string;
  delivered_qty: number;
  shortfall: number;
  customer?: string;
}

export interface Shipment {
  id: string;
  sku: string;
  qty: number;
  origin: string;
  dest: string;
  route_id: string;
  eta: number;
  status: string;
  order_id: string | null;
  kind: string;
  vendor_id: string | null;
  source_warehouse: string | null;
  cost: number;
  carbon: number;
}

export interface WorldState {
  day: number;
  warehouses: Record<string, any>;
  skus: Record<string, any>;
  vendors: Record<string, any>;
  routes: Record<string, any>;
  inventory: Record<string, Record<string, number>>;
  orders: Record<string, Order>;
  shipments: Record<string, Shipment>;
  kpis: Kpis;
  issues: Issues[];
  risk_orders: any[];
  objectives: any;
}

export interface TraceEvent {
  step: string;
  day?: number;
  summary?: string;
  passed?: boolean;
  issues_after?: string[];
  choice?: string;
  justification?: string;
  actions?: string[];
  candidate_ids?: string[];
  selected_ids?: string[];
  solver_status?: string;
  delta_cost?: number;
  delta_carbon?: number;
}

export interface AgentTrace {
  run_id: string;
  trace: TraceEvent[];
  status: string;
  decision: any;
  verification: any;
}

export interface EventLogRow {
  id: number;
  seq: number;
  day: number;
  type: string;
  payload: Record<string, any>;
}