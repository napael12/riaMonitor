import axios from "axios";
import type { Adviser, Change, PagedResponse, Snapshot } from "./types";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// Adviser list params
// ---------------------------------------------------------------------------
export interface AdviserListParams {
  q?: string;
  state?: string;
  min_aum?: number;
  max_aum?: number;
  registration_type?: string;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// Changes list params
// ---------------------------------------------------------------------------
export interface ChangesListParams {
  period?: string;
  field?: string;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getAdvisers(
  params: AdviserListParams = {}
): Promise<PagedResponse<Adviser>> {
  const { data } = await client.get<PagedResponse<Adviser>>("/advisers", {
    params,
  });
  return data;
}

export async function getAdviser(crd: string): Promise<Adviser> {
  const { data } = await client.get<Adviser>(`/advisers/${crd}`);
  return data;
}

export async function getAdviserHistory(crd: string): Promise<Snapshot[]> {
  const { data } = await client.get<Snapshot[]>(`/advisers/${crd}/history`);
  return data;
}

export async function getAdviserChanges(crd: string): Promise<Change[]> {
  const { data } = await client.get<Change[]>(`/advisers/${crd}/changes`);
  return data;
}

export async function getChanges(
  params: ChangesListParams = {}
): Promise<PagedResponse<Change>> {
  const { data } = await client.get<PagedResponse<Change>>("/changes", {
    params,
  });
  return data;
}
