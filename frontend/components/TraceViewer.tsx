"use client";

import { useState, useEffect } from "react";
import { 
  Activity, 
  Clock, 
  Cpu, 
  DollarSign, 
  CheckCircle2, 
  Layers, 
  Split, 
  Sparkles, 
  ShieldAlert, 
  BarChart, 
  Search,
  ArrowRight
} from "lucide-react";
import { api, RequestTrace } from "@/lib/api";

interface TraceViewerProps {
  requestId?: string;
}

export default function TraceViewer({ requestId = "demo-trace" }: TraceViewerProps) {
  const [trace, setTrace] = useState<RequestTrace | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"waterfall" | "candidates" | "validation">("waterfall");

  useEffect(() => {
    loadTrace(requestId);
  }, [requestId]);

  const loadTrace = async (id: string) => {
    setLoading(true);
    try {
      const data = await api.getTrace(id);
      setTrace(data);
    } catch (e) {
      console.error("Failed to load trace:", e);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !trace) {
    return (
      <div style={{ textAlign: "center", padding: "80px 20px" }}>
        <div 
          className="spin-animation" 
          style={{ width: "28px", height: "28px", border: "2px solid var(--accent-primary)", borderTopColor: "transparent", borderRadius: "50%", margin: "0 auto 16px" }} 
        />
        <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Loading request telemetry and pipeline breakdown...</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Overview Metric Banner */}
      <div 
        className="glass-panel" 
        style={{ 
          padding: "24px", 
          background: "radial-gradient(ellipse at top left, rgba(6, 182, 212, 0.1) 0%, rgba(15, 20, 29, 0.8) 70%)" 
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "16px", marginBottom: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
              <span className="badge badge-brand">Request Trace</span>
              <span style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--text-muted)" }}>
                ID: {trace.request_id}
              </span>
            </div>
            <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#ffffff" }}>
              &ldquo;{trace.query}&rdquo;
            </h2>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span className="badge badge-high" style={{ padding: "6px 12px", fontSize: "12px" }}>
              <CheckCircle2 size={13} /> Validation Passed
            </span>
          </div>
        </div>

        {/* Latency & Token Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)", fontSize: "11px" }}>
              <Clock size={12} color="var(--accent-secondary)" /> Total Latency
            </div>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#ffffff", marginTop: "4px", fontFamily: "monospace" }}>
              {trace.total_latency_ms} <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>ms</span>
            </div>
          </div>

          <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)", fontSize: "11px" }}>
              <Cpu size={12} color="var(--accent-primary)" /> Routing Decision
            </div>
            <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--accent-secondary)", marginTop: "6px" }}>
              {trace.route}
            </div>
          </div>

          <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)", fontSize: "11px" }}>
              <Sparkles size={12} color="var(--accent-emerald)" /> Token Usage
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: "#ffffff", marginTop: "4px", fontFamily: "monospace" }}>
              {trace.token_count_input} <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>in</span> / {trace.token_count_output} <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>out</span>
            </div>
          </div>

          <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)", fontSize: "11px" }}>
              <DollarSign size={12} color="var(--accent-amber)" /> Est. Cost
            </div>
            <div style={{ fontSize: "18px", fontWeight: 700, color: "#ffffff", marginTop: "4px", fontFamily: "monospace" }}>
              ${trace.cost_estimate_usd.toFixed(4)}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
        <button
          onClick={() => setActiveTab("waterfall")}
          className="btn"
          style={{
            background: activeTab === "waterfall" ? "rgba(99, 102, 241, 0.15)" : "transparent",
            color: activeTab === "waterfall" ? "#ffffff" : "var(--text-muted)",
            borderColor: activeTab === "waterfall" ? "rgba(99, 102, 241, 0.3)" : "transparent",
            fontSize: "12px",
            padding: "8px 14px",
          }}
        >
          <Activity size={13} /> Pipeline Waterfall
        </button>
        <button
          onClick={() => setActiveTab("candidates")}
          className="btn"
          style={{
            background: activeTab === "candidates" ? "rgba(99, 102, 241, 0.15)" : "transparent",
            color: activeTab === "candidates" ? "#ffffff" : "var(--text-muted)",
            borderColor: activeTab === "candidates" ? "rgba(99, 102, 241, 0.3)" : "transparent",
            fontSize: "12px",
            padding: "8px 14px",
          }}
        >
          <Search size={13} /> Retrieval &amp; Reranking Candidates
        </button>
        <button
          onClick={() => setActiveTab("validation")}
          className="btn"
          style={{
            background: activeTab === "validation" ? "rgba(99, 102, 241, 0.15)" : "transparent",
            color: activeTab === "validation" ? "#ffffff" : "var(--text-muted)",
            borderColor: activeTab === "validation" ? "rgba(99, 102, 241, 0.3)" : "transparent",
            fontSize: "12px",
            padding: "8px 14px",
          }}
        >
          <ShieldAlert size={13} /> Grounding &amp; Faithfulness Audit
        </button>
      </div>

      {/* Tab 1: Waterfall */}
      {activeTab === "waterfall" && (
        <div className="glass-panel" style={{ padding: "20px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff", marginBottom: "16px" }}>
            Execution Timeline Waterfall
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {trace.stages.map((stage) => {
              const pct = Math.max(4, Math.round((stage.latency_ms / trace.total_latency_ms) * 100));
              return (
                <div key={stage.name} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12px" }}>
                    <span style={{ fontWeight: 600, color: "#f8fafc" }}>{stage.name}</span>
                    <span style={{ fontFamily: "monospace", color: "var(--accent-secondary)" }}>
                      {stage.latency_ms} ms ({pct}%)
                    </span>
                  </div>

                  <div style={{ width: "100%", height: "8px", background: "rgba(255, 255, 255, 0.06)", borderRadius: "4px", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${pct}%`,
                        height: "100%",
                        background: "var(--grad-brand)",
                        borderRadius: "4px",
                      }}
                    />
                  </div>

                  {/* Stage Meta Details */}
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "2px" }}>
                    {Object.entries(stage.details).map(([k, v]) => (
                      <span
                        key={k}
                        style={{
                          fontSize: "10px",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          background: "rgba(0,0,0,0.3)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--text-muted)",
                          fontFamily: "monospace",
                        }}
                      >
                        {k}: <strong style={{ color: "var(--text-secondary)" }}>{String(v)}</strong>
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Candidates */}
      {activeTab === "candidates" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          {/* Top-N Retrieved Chunks */}
          <div className="glass-panel" style={{ padding: "18px" }}>
            <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={16} color="var(--accent-secondary)" />
              Top-N Hybrid Candidates ({trace.retrieved_chunks.length})
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {trace.retrieved_chunks.map((c) => (
                <div key={c.id} style={{ padding: "10px 12px", background: "rgba(0,0,0,0.3)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 600, color: "#ffffff" }}>{c.document_name}</span>
                    <span className="badge badge-brand" style={{ fontSize: "9px" }}>{c.method}</span>
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)", fontStyle: "italic", lineHeight: 1.4 }}>
                    &ldquo;{c.preview}&rdquo;
                  </p>
                  <div style={{ marginTop: "6px", fontSize: "10px", color: "var(--accent-secondary)", fontFamily: "monospace" }}>
                    Fused Score: {(c.score).toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top-K Reranked Chunks */}
          <div className="glass-panel" style={{ padding: "18px" }}>
            <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Sparkles size={16} color="var(--accent-emerald)" />
              Top-K Cross-Encoder Reranked ({trace.reranked_chunks.length})
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {trace.reranked_chunks.map((c) => (
                <div key={c.id} style={{ padding: "10px 12px", background: "rgba(16, 185, 129, 0.05)", borderRadius: "var(--radius-md)", border: "1px solid rgba(16, 185, 129, 0.25)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 600, color: "#ffffff" }}>{c.document_name}</span>
                    <span className="badge badge-high" style={{ fontSize: "9px" }}>Selected</span>
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", lineHeight: 1.4 }}>
                    &ldquo;{c.preview}&rdquo;
                  </p>
                  <div style={{ marginTop: "6px", fontSize: "10px", color: "#34d399", fontFamily: "monospace" }}>
                    Rerank Score: {(c.score).toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Validation */}
      {activeTab === "validation" && (
        <div className="glass-panel" style={{ padding: "20px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff", marginBottom: "16px" }}>
            Deterministic Grounding &amp; Citation Audit
          </h3>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ padding: "16px", background: "rgba(0,0,0,0.3)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Faithfulness Verification</div>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--accent-emerald)", marginTop: "4px", fontFamily: "monospace" }}>
                {(trace.validation_result.faithfulness_score * 100).toFixed(1)}%
              </div>
              <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
                All generated claims cross-referenced against reranked context passages.
              </p>
            </div>

            <div style={{ padding: "16px", background: "rgba(0,0,0,0.3)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Citation Precision</div>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--accent-secondary)", marginTop: "4px", fontFamily: "monospace" }}>
                {(trace.validation_result.citation_precision * 100).toFixed(1)}%
              </div>
              <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
                Zero ghost citations: every cited chunk exists in the retrieved set.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
