import { useQuery } from "@tanstack/react-query";
import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAdvisers } from "../api";
import type { Adviser } from "../types";

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY","DC",
];

const PAGE_SIZE = 50;

function formatAUM(val: number | null): string {
  if (val == null) return "—";
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  return `$${val.toLocaleString()}`;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

export default function AdvisersPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [state, setState] = useState("");
  const [regType, setRegType] = useState("");
  const [minAUM, setMinAUM] = useState("");
  const [maxAUM, setMaxAUM] = useState("");
  const [offset, setOffset] = useState(0);

  const debouncedSearch = useDebounce(search, 300);

  // Reset to page 1 when filters change
  useEffect(() => {
    setOffset(0);
  }, [debouncedSearch, state, regType, minAUM, maxAUM]);

  const queryParams = {
    ...(debouncedSearch ? { q: debouncedSearch } : {}),
    ...(state ? { state } : {}),
    ...(regType ? { registration_type: regType } : {}),
    ...(minAUM ? { min_aum: Number(minAUM) } : {}),
    ...(maxAUM ? { max_aum: Number(maxAUM) } : {}),
    limit: PAGE_SIZE,
    offset,
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ["advisers", queryParams],
    queryFn: () => getAdvisers(queryParams),
    placeholderData: (prev) => prev,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const handleRowClick = useCallback(
    (crd: string) => navigate(`/advisers/${crd}`),
    [navigate]
  );

  const inputStyle: React.CSSProperties = {
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    padding: "0.45rem 0.75rem",
    fontSize: "0.9rem",
    outline: "none",
    background: "#fff",
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ marginBottom: "1.5rem", fontSize: "1.6rem", fontWeight: 700 }}>
        Adviser Search
      </h1>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.75rem",
          marginBottom: "1.25rem",
          background: "#fff",
          borderRadius: "10px",
          padding: "1rem 1.25rem",
          boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
        }}
      >
        <input
          style={{ ...inputStyle, minWidth: "240px", flex: "2" }}
          placeholder="Search firm name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          style={{ ...inputStyle, minWidth: "120px" }}
          value={state}
          onChange={(e) => setState(e.target.value)}
        >
          <option value="">All States</option>
          {US_STATES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          style={{ ...inputStyle, minWidth: "150px" }}
          value={regType}
          onChange={(e) => setRegType(e.target.value)}
        >
          <option value="">All Types</option>
          <option value="SEC">SEC Registered</option>
          <option value="Exempt">Exempt Reporting</option>
        </select>
        <input
          style={{ ...inputStyle, width: "130px" }}
          placeholder="Min AUM ($)"
          type="number"
          value={minAUM}
          onChange={(e) => setMinAUM(e.target.value)}
        />
        <input
          style={{ ...inputStyle, width: "130px" }}
          placeholder="Max AUM ($)"
          type="number"
          value={maxAUM}
          onChange={(e) => setMaxAUM(e.target.value)}
        />
        <button
          style={{
            border: "1px solid #d1d5db",
            borderRadius: "6px",
            padding: "0.45rem 1rem",
            background: "#f3f4f6",
            cursor: "pointer",
            fontSize: "0.9rem",
          }}
          onClick={() => {
            setSearch("");
            setState("");
            setRegType("");
            setMinAUM("");
            setMaxAUM("");
          }}
        >
          Clear
        </button>
      </div>

      {/* Results info */}
      <div style={{ marginBottom: "0.75rem", color: "#6b7280", fontSize: "0.9rem" }}>
        {isLoading
          ? "Loading…"
          : data
          ? `Showing ${data.items.length} of ${data.total.toLocaleString()} advisers`
          : ""}
      </div>

      {error && (
        <div style={{ color: "#dc2626", marginBottom: "1rem" }}>
          Error loading advisers. Ensure the API is running.
        </div>
      )}

      {/* Table */}
      <div
        style={{
          background: "#fff",
          borderRadius: "10px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
          overflow: "hidden",
          marginBottom: "1rem",
        }}
      >
        <div style={{ overflowX: "auto" }}>
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}
          >
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                {["Firm Name", "CRD", "State", "Type", "AUM", "Employees", "Period"].map(
                  (h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "0.65rem 1rem",
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
              {isLoading ? (
                <tr>
                  <td colSpan={7} style={{ padding: "2rem", textAlign: "center", color: "#6b7280" }}>
                    Loading…
                  </td>
                </tr>
              ) : !data?.items.length ? (
                <tr>
                  <td colSpan={7} style={{ padding: "2rem", textAlign: "center", color: "#6b7280" }}>
                    No advisers found. Try adjusting your filters.
                  </td>
                </tr>
              ) : (
                data.items.map((a: Adviser, i: number) => (
                  <tr
                    key={a.crd}
                    onClick={() => handleRowClick(a.crd)}
                    style={{
                      background: i % 2 === 0 ? "#fff" : "#f9fafb",
                      cursor: "pointer",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "#eff6ff")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background =
                        i % 2 === 0 ? "#fff" : "#f9fafb")
                    }
                  >
                    <td
                      style={{
                        padding: "0.6rem 1rem",
                        maxWidth: "280px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        fontWeight: 500,
                        color: "#2563eb",
                      }}
                    >
                      {a.firm_name}
                    </td>
                    <td
                      style={{
                        padding: "0.6rem 1rem",
                        fontFamily: "monospace",
                        fontSize: "0.85rem",
                      }}
                    >
                      {a.crd}
                    </td>
                    <td style={{ padding: "0.6rem 1rem" }}>{a.primary_state ?? "—"}</td>
                    <td style={{ padding: "0.6rem 1rem" }}>
                      <span
                        style={{
                          background:
                            a.registration_type === "SEC" ? "#dbeafe" : "#f3e8ff",
                          color:
                            a.registration_type === "SEC" ? "#1d4ed8" : "#7c3aed",
                          borderRadius: "4px",
                          padding: "2px 8px",
                          fontSize: "0.78rem",
                          fontWeight: 600,
                        }}
                      >
                        {a.registration_type ?? "—"}
                      </span>
                    </td>
                    <td style={{ padding: "0.6rem 1rem", textAlign: "right" }}>
                      {formatAUM(a.aum)}
                    </td>
                    <td style={{ padding: "0.6rem 1rem", textAlign: "right" }}>
                      {a.employees != null ? a.employees.toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "0.6rem 1rem", color: "#6b7280" }}>
                      {a.latest_period ?? "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            justifyContent: "flex-end",
          }}
        >
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            style={{
              padding: "0.4rem 1rem",
              borderRadius: "6px",
              border: "1px solid #d1d5db",
              background: offset === 0 ? "#f3f4f6" : "#fff",
              cursor: offset === 0 ? "not-allowed" : "pointer",
              color: offset === 0 ? "#9ca3af" : "#374151",
            }}
          >
            Previous
          </button>
          <span style={{ color: "#6b7280", fontSize: "0.9rem" }}>
            Page {currentPage} of {totalPages}
          </span>
          <button
            disabled={offset + PAGE_SIZE >= (data?.total ?? 0)}
            onClick={() => setOffset(offset + PAGE_SIZE)}
            style={{
              padding: "0.4rem 1rem",
              borderRadius: "6px",
              border: "1px solid #d1d5db",
              background:
                offset + PAGE_SIZE >= (data?.total ?? 0) ? "#f3f4f6" : "#fff",
              cursor:
                offset + PAGE_SIZE >= (data?.total ?? 0)
                  ? "not-allowed"
                  : "pointer",
              color:
                offset + PAGE_SIZE >= (data?.total ?? 0)
                  ? "#9ca3af"
                  : "#374151",
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
