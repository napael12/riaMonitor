import { useQuery } from "@tanstack/react-query";
import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAdviser, getAdviserChanges, getAdviserHistory } from "../api";
import type { Change, Snapshot } from "../types";

function formatAUM(val: number | null | undefined): string {
  if (val == null) return "—";
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  return `$${val.toLocaleString()}`;
}

function formatNum(val: number | null | undefined): string {
  if (val == null) return "—";
  return val.toLocaleString();
}

const sectionStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: "10px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
  overflow: "hidden",
  marginBottom: "1.5rem",
};

const sectionHeaderStyle: React.CSSProperties = {
  padding: "1rem 1.5rem",
  borderBottom: "1px solid #e5e7eb",
  fontWeight: 600,
  fontSize: "1rem",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.6rem 1rem",
  color: "#6b7280",
  fontWeight: 600,
  fontSize: "0.78rem",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  borderBottom: "1px solid #e5e7eb",
  whiteSpace: "nowrap",
  background: "#f9fafb",
};

const tdStyle: React.CSSProperties = {
  padding: "0.55rem 1rem",
};

export default function AdviserDetailPage() {
  const { crd } = useParams<{ crd: string }>();
  const navigate = useNavigate();

  const {
    data: adviser,
    isLoading: adviserLoading,
    error: adviserError,
  } = useQuery({
    queryKey: ["adviser", crd],
    queryFn: () => getAdviser(crd!),
    enabled: !!crd,
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["adviser-history", crd],
    queryFn: () => getAdviserHistory(crd!),
    enabled: !!crd,
  });

  const { data: changes, isLoading: changesLoading } = useQuery({
    queryKey: ["adviser-changes", crd],
    queryFn: () => getAdviserChanges(crd!),
    enabled: !!crd,
  });

  if (adviserLoading) {
    return <div style={{ padding: "2rem", color: "#6b7280" }}>Loading adviser…</div>;
  }

  if (adviserError || !adviser) {
    return (
      <div style={{ padding: "2rem", color: "#dc2626" }}>
        Adviser not found or API unavailable.{" "}
        <button
          onClick={() => navigate(-1)}
          style={{ cursor: "pointer", color: "#2563eb", background: "none", border: "none", textDecoration: "underline" }}
        >
          Go back
        </button>
      </div>
    );
  }

  // Chart data: sort history ascending for chart display
  const chartData = (history ?? [])
    .slice()
    .sort((a: Snapshot, b: Snapshot) => a.period.localeCompare(b.period))
    .map((s: Snapshot) => ({
      period: s.period,
      aum: s.aum != null ? s.aum / 1e6 : null, // display in $M
      employees: s.employees,
    }));

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1rem" }}>
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        style={{
          background: "none",
          border: "none",
          color: "#2563eb",
          cursor: "pointer",
          fontSize: "0.9rem",
          marginBottom: "1rem",
          padding: 0,
          textDecoration: "underline",
        }}
      >
        ← Back
      </button>

      {/* Profile card */}
      <div style={{ ...sectionStyle, marginBottom: "1.5rem" }}>
        <div style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "1.5rem", flexWrap: "wrap" }}>
            <div style={{ flex: "1", minWidth: "240px" }}>
              <h1 style={{ margin: "0 0 0.25rem", fontSize: "1.5rem", fontWeight: 700 }}>
                {adviser.firm_name}
              </h1>
              <div style={{ color: "#6b7280", fontSize: "0.9rem", marginBottom: "1rem" }}>
                CRD: <span style={{ fontFamily: "monospace" }}>{adviser.crd}</span>
                {adviser.sec_number && (
                  <>
                    {" | SEC#: "}
                    <span style={{ fontFamily: "monospace" }}>{adviser.sec_number}</span>
                  </>
                )}
              </div>
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                {adviser.registration_type && (
                  <span
                    style={{
                      background: adviser.registration_type === "SEC" ? "#dbeafe" : "#f3e8ff",
                      color: adviser.registration_type === "SEC" ? "#1d4ed8" : "#7c3aed",
                      borderRadius: "6px",
                      padding: "4px 12px",
                      fontWeight: 600,
                      fontSize: "0.82rem",
                    }}
                  >
                    {adviser.registration_type === "SEC" ? "SEC Registered" : "Exempt Reporting"}
                  </span>
                )}
                {adviser.primary_state && (
                  <span
                    style={{
                      background: "#f0fdf4",
                      color: "#15803d",
                      borderRadius: "6px",
                      padding: "4px 12px",
                      fontWeight: 600,
                      fontSize: "0.82rem",
                    }}
                  >
                    {adviser.primary_state}
                  </span>
                )}
                {adviser.latest_snapshot?.registration_status && (
                  <span
                    style={{
                      background: "#fff7ed",
                      color: "#c2410c",
                      borderRadius: "6px",
                      padding: "4px 12px",
                      fontWeight: 600,
                      fontSize: "0.82rem",
                    }}
                  >
                    {adviser.latest_snapshot.registration_status}
                  </span>
                )}
              </div>
            </div>

            {/* Key stats */}
            <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.75rem", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>AUM</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>
                  {formatAUM(adviser.latest_snapshot?.aum)}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.75rem", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Employees</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>
                  {formatNum(adviser.latest_snapshot?.employees)}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.75rem", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Clients</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>
                  {formatNum(adviser.latest_snapshot?.num_clients)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AUM History Chart */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>AUM History ($M)</div>
        <div style={{ padding: "1rem 1.5rem 1.5rem" }}>
          {historyLoading ? (
            <div style={{ color: "#6b7280" }}>Loading chart…</div>
          ) : chartData.length < 2 ? (
            <div style={{ color: "#6b7280" }}>
              Not enough historical data to display a chart. At least 2 periods required.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 12, fill: "#6b7280" }}
                  angle={-30}
                  textAnchor="end"
                  height={50}
                />
                <YAxis
                  tickFormatter={(v) => `$${v.toFixed(0)}M`}
                  tick={{ fontSize: 12, fill: "#6b7280" }}
                  width={80}
                />
                <Tooltip
                  formatter={(value: number) => [`$${value?.toFixed(1)}M`, "AUM"]}
                />
                <Line
                  type="monotone"
                  dataKey="aum"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Employee History Chart */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Employee Count History</div>
        <div style={{ padding: "1rem 1.5rem 1.5rem" }}>
          {historyLoading ? (
            <div style={{ color: "#6b7280" }}>Loading chart…</div>
          ) : chartData.length < 2 ? (
            <div style={{ color: "#6b7280" }}>
              Not enough historical data to display a chart.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 12, fill: "#6b7280" }}
                  angle={-30}
                  textAnchor="end"
                  height={50}
                />
                <YAxis tick={{ fontSize: 12, fill: "#6b7280" }} width={60} />
                <Tooltip formatter={(value: number) => [value?.toLocaleString(), "Employees"]} />
                <Line
                  type="monotone"
                  dataKey="employees"
                  stroke="#7c3aed"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Change Log */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Change Log</div>
        {changesLoading ? (
          <div style={{ padding: "1.5rem", color: "#6b7280" }}>Loading…</div>
        ) : !changes?.length ? (
          <div style={{ padding: "1.5rem", color: "#6b7280" }}>
            No changes recorded yet. Run multiple ETL periods to detect changes.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Period</th>
                  <th style={thStyle}>Field</th>
                  <th style={thStyle}>Old Value</th>
                  <th style={thStyle}>New Value</th>
                  <th style={thStyle}>Detected</th>
                </tr>
              </thead>
              <tbody>
                {changes.map((c: Change, i: number) => (
                  <tr
                    key={c.id}
                    style={{ background: i % 2 === 0 ? "#fff" : "#f9fafb" }}
                  >
                    <td style={tdStyle}>{c.period_to ?? "—"}</td>
                    <td style={{ ...tdStyle, fontWeight: 600 }}>{c.field ?? "—"}</td>
                    <td style={{ ...tdStyle, color: "#dc2626" }}>{c.old_value ?? "—"}</td>
                    <td style={{ ...tdStyle, color: "#16a34a" }}>{c.new_value ?? "—"}</td>
                    <td style={{ ...tdStyle, color: "#6b7280", fontSize: "0.82rem" }}>
                      {c.detected_at
                        ? new Date(c.detected_at).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Snapshot History Table */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Snapshot History</div>
        {historyLoading ? (
          <div style={{ padding: "1.5rem", color: "#6b7280" }}>Loading…</div>
        ) : !history?.length ? (
          <div style={{ padding: "1.5rem", color: "#6b7280" }}>No snapshots found.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
              <thead>
                <tr>
                  {["Period", "AUM", "Employees", "Clients", "Status"].map((h) => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map((s: Snapshot, i: number) => (
                  <tr key={s.id} style={{ background: i % 2 === 0 ? "#fff" : "#f9fafb" }}>
                    <td style={{ ...tdStyle, fontWeight: 500 }}>{s.period}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{formatAUM(s.aum)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{formatNum(s.employees)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{formatNum(s.num_clients)}</td>
                    <td style={tdStyle}>{s.registration_status ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
