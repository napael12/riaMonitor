export interface Adviser {
  crd: string;
  firm_name: string;
  registration_type: string | null;
  sec_number: string | null;
  primary_state: string | null;
  aum: number | null;
  employees: number | null;
  num_clients: number | null;
  registration_status: string | null;
  latest_period: string | null;
  created_at?: string;
  updated_at?: string;
  latest_snapshot?: Snapshot | null;
}

export interface Snapshot {
  id: number;
  adviser_crd: string;
  period: string;
  aum: number | null;
  employees: number | null;
  num_clients: number | null;
  registration_status: string | null;
  ingested_at: string | null;
}

export interface Change {
  id: number;
  adviser_crd: string;
  period_from: string | null;
  period_to: string | null;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  detected_at: string | null;
}

export interface PagedResponse<T> {
  total: number;
  items: T[];
  offset: number;
  limit: number;
}
