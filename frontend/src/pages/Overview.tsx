import { useQuery } from "@tanstack/react-query";
import React from "react";
import { getAdvisers, getChanges } from "../api";
import type { Adviser } from "../types";

const cardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: "10px",
  padding: "1.5rem 2rem",
  boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
  minWidth: "180px",
  flex: "1",
};

const statLabelStyle: React.CSSProperties = {
  fontSize: "0.8rem",
  color: "#6b7280",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: "0.4rem",
};

const statValueStyle: React.CSSProperties = {
  fontSize: "2rem",
  fontWeight: 700,
  color: "#1a1a2e",
};

function formatAUM(val: number | null): string {
  if (val == null) return "N/A";
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  return `$${val.toLocaleString()}`;
}

function formatNumber(val: number | null): string {
  if (val == null) return "N/A";
  return val.toLocaleString();
}

export default function Overview() {
  const {
    data: advisersData,
    isLoading: advisersLoading,
    error: advisersError,
  } = useQuery({
    queryKey: ["advisers-overview"],
    queryFn: () => getAdvisers({ limit: 500, offset: 0 }),
  });

  const {
    data: secData,
  } = useQuery({
    queryKey: ["advisers-sec"],
    queryFn: () => getAdvisers({ registration_type: "SEC", limit: 1 }),
  });

  const {
    data: exemptData,
  } = useQuery({
    queryKey: ["advisers-exempt"],
    queryFn: () => getAdvisers({ registration_type: "Exempt", limit: 1 }),
  });

  const {
    data: changesData,
    isLoading: changesLoading,
  } = useQuery({
    queryKey: ["changes-recent"],
    queryFn: () => getChanges({ limit: 10 }),
  });

  const totalAUM = React.useMemo(() => {
    if (!advisersData) return null;
    const sum = advisersData.items.reduce(
      (acc: number, a: Adviser) => acc + (a.aum ?? 0),
      0
    );
    return sum;
  }, [advisersData]);

  const latestPeriod = React.useMemo(() => {
    if (!advisersData?.items.length) return null;
    const periods = advisersData.items
      .map((a: Adviser) => a.latest_period)
      .filter(Boolean);
    if (!periods.length) return null;
    return periods.sort().reverse()[0];
  }, [advisersData]);

  if (advisersError) {
    return (
      <div style={{ padding: "2rem", color: "#dc2626" }}>
        Error loading data. Ensure the API is running and the database has been seeded.
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ marginBottom: "0.25rem", fontSize: "1.6rem", fontWeight: 700 }}>
        Market Overview
      </h1>
      {latestPeriod && (
        <p style={{ color: "#6b7280", marginBottom: "1.5rem" }}>
          Latest data period: <strong>{latestPeriod}</strong>
        </p>
      )}

      {/* Stat cards */}
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "2rem" }}>
        <div style={cardStyle}>
          <div style={statLabelStyle}>Total Advisers</div>
          <div style={statValueStyle}>
            {advisersLoading ? "…" : formatNumber(advisersData?.total ?? null)}
          </div>
        </div>
        <div style={cardStyle}>
          <div style={statLabelStyle}>SEC Registered</div>
          <div style={statValueStyle}>
            {secData == null ? "…" : formatNumber(secData.total)}
          </div>
        </div>
        <div style={cardStyle}>
          <div style={statLabelStyle}>Exempt Reporting</div>
          <div style={statValueStyle}>
            {exemptData == null ? "…" : formatNumber(exemptData.total)}
          </div>
        </div>
        <div style={cardStyle}>
          <div style={statLabelStyle}>Total AUM (sample)</div>
          <div style={statValueStyle}>
            {advisersLoading ? "…" : formatAUM(totalAUM)}
          </div>
        </div>
        <div style={cardStyle}>
          <div style={statLabelStyle}>Recent Changes</div>
          <div style={statValueStyle}>
            {changesLoading ? "…" : formatNumber(changesData?.total ?? null)}
          </div>
        </div>
      </div>

      {/* Latest period summary table */}
      <div
        style={{
          background: "#fff",
          borderRadius: "10px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
          overflow: "hidden",
          marginBottom: "2rem",
        }}
      >
        <div
          style={{
            padding: "1rem 1.5rem",
            borderBottom: "1px solid #e5e7eb",
            fontWeight: 600,
            fontSize: "1rem",
          }}
        >
          Adviser Sample (up to 500, latest period)
        </div>
        {advisersLoading ? (
          <div style={{ padding: "1.5rem", color: "#6b7280" }}>Loading…</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  {["Firm Name", "CRD", "State", "Type", "AUM", "Employees", "Period"].map(
                    (h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left",
                          padding: "0.6rem 1rem",
                          color: "#6b7280",
                          fontWeight: 600,
                          fontSize: "0.78rem",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                          borderBottom: "1px solid #e5e7eb",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {(advisersData?.items ?? []).map((a: Adviser, i: number) => (
                  <tr
                    key={a.crd}
                    style={{ background: i % 2 === 0 ? "#fff" : "#f9fafb" }}
                  >
                    <td style={{ padding: "0.55rem 1rem", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {a.firm_name}
                    </td>
                    <td style={{ padding: "0.55rem 1rem", fontFamily: "monospace", fontSize: "0.85rem" }}>{a.crd}</td>
                    <td style={{ padding: "0.55rem 1rem" }}>{a.primary_state ?? "—"}</td>
                    <td style={{ padding: "0.55rem 1rem" }}>
                      <span
                        style={{
                          background: a.registration_type === "SEC" ? "#dbeafe" : "#f3e8ff",
                          color: a.registration_type === "SEC" ? "#1d4ed8" : "#7c3aed",
                          borderRadius: "4px",
                          padding: "2px 8px",
                          fontSize: "0.78rem",
                          fontWeight: 600,
                        }}
                      >
                        {a.registration_type ?? "—"}
                      </span>
                    </td>
                    <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>
                      {formatAUM(a.aum)}
                    </td>
                    <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>
                      {a.employees != null ? a.employees.toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "0.55rem 1rem", color: "#6b7280" }}>
                      {a.latest_period ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent changes */}
      <div
        style={{
          background: "#fff",
          borderRadius: "10px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "1rem 1.5rem",
            borderBottom: "1px solid #e5e7eb",
            fontWeight: 600,
            fontSize: "1rem",
          }}
        >
          Recent Changes
        </div>
        {changesLoading ? (
          <div style={{ padding: "1.5rem", color: "#6b7280" }}>Loading…</div>
        ) : !changesData?.items.length ? (
          <div style={{ padding: "1.5rem", color: "#6b7280" }}>
            No changes recorded yet. Run the ETL pipeline to detect changes.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  {["CRD", "Period", "Field", "Old Value", "New Value"].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "0.6rem 1rem",
                        color: "#6b7280",
                        fontWeight: 600,
                        fontSize: "0.78rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        borderBottom: "1px solid #e5e7eb",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {changesData.items.map((c, i) => (
                  <tr key={c.id} style={{ background: i % 2 === 0 ? "#fff" : "#f9fafb" }}>
                    <td style={{ padding: "0.55rem 1rem", fontFamily: "monospace", fontSize: "0.85rem" }}>
                      {c.adviser_crd}
                    </td>
                    <td style={{ padding: "0.55rem 1rem" }}>{c.period_to ?? "—"}</td>
                    <td style={{ padding: "0.55rem 1rem", fontWeight: 500 }}>{c.field ?? "—"}</td>
                    <td style={{ padding: "0.55rem 1rem", color: "#dc2626" }}>{c.old_value ?? "—"}</td>
                    <td style={{ padding: "0.55rem 1rem", color: "#16a34a" }}>{c.new_value ?? "—"}</td>
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
