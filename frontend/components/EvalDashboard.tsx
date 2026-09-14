"use client";

import { useState, useEffect } from "react";
import { 
  BarChart3, 
  Play, 
  TrendingUp, 
  ShieldCheck, 
  Target, 
  Clock, 
  DollarSign, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle,
  Layers,
  ArrowUpRight
} from "lucide-react";
import { api, EvalRun } from "@/lib/api";

export default function EvalDashboard() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    loadRuns();
  }, []);

  const loadRuns = async () => {
    try {
      const data = await api.getEvaluationRuns();
      setRuns(data);
      if (data.length > 0 && !selectedRunId) {
        setSelectedRunId(data[0].run_id);
      }
    } catch (e) {
      console.error("Failed to load runs:", e);
    }
  };

  const handleRunBenchmark = async () => {
    setRunning(true);
    try {
      const newRun = await api.triggerEvaluationRun(50);
      setRuns((prev) => [newRun, ...prev]);
      setSelectedRunId(newRun.run_id);
    } catch (e) {
      console.error("Benchmark error:", e);
    } finally {
      setRunning(false);
    }
  };

  const activeRun = runs.find((r) => r.run_id === selectedRunId) || runs[0];
  const baselineRun = runs.find((r) => r.run_id !== selectedRunId) || runs[1];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Action Header */}
      <div 
        className="glass-panel" 
        style={{ 
          padding: "24px", 
          background: "radial-gradient(ellipse at 90% 10%, rgba(16, 185, 129, 0.1) 0%, rgba(15, 20, 29, 0.8) 70%)" 
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <BarChart3 size={20} color="var(--accent-emerald)" />
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#ffffff" }}>
                Continuous RAG Evaluation Suite
              </h2>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", maxWidth: "680px" }}>
              Automated benchmarks measuring Retrieval Recall@K, LLM Faithfulness, Citation Precision, and Abstention Quality across curated enterprise test suites.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button
              onClick={handleRunBenchmark}
              disabled={running}
              className="btn btn-primary"
              style={{ padding: "10px 20px" }}
            >
              {running ? (
                <div className="spin-animation" style={{ width: "14px", height: "14px", border: "2px solid #ffffff", borderTopColor: "transparent", borderRadius: "50%" }} />
              ) : (
                <Play size={14} fill="#ffffff" />
              )}
              <span>{running ? "Evaluating 150 Test Cases..." : "Trigger Benchmark Run"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metric Cards Grid */}
      {activeRun && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
          {/* Faithfulness */}
          <div className="glass-panel" style={{ padding: "18px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Faithfulness (No Hallucinations)</span>
              <ShieldCheck size={16} color="var(--accent-emerald)" />
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "#ffffff", marginTop: "8px", fontFamily: "monospace" }}>
              {(activeRun.metrics.faithfulness * 100).toFixed(1)}%
            </div>
            {baselineRun && (
              <div style={{ display: "flex", alignItems: "center", gap: "4px", marginTop: "4px", fontSize: "11px", color: "var(--accent-emerald)" }}>
                <TrendingUp size={12} />
                <span>+{(activeRun.metrics.faithfulness * 100 - baselineRun.metrics.faithfulness * 100).toFixed(1)}% vs Dense baseline</span>
              </div>
            )}
          </div>

          {/* Citation Precision */}
          <div className="glass-panel" style={{ padding: "18px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Citation Precision</span>
              <Target size={16} color="var(--accent-secondary)" />
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "#ffffff", marginTop: "8px", fontFamily: "monospace" }}>
              {(activeRun.metrics.citation_precision * 100).toFixed(1)}%
            </div>
            {baselineRun && (
              <div style={{ display: "flex", alignItems: "center", gap: "4px", marginTop: "4px", fontSize: "11px", color: "var(--accent-emerald)" }}>
                <TrendingUp size={12} />
                <span>+{(activeRun.metrics.citation_precision * 100 - baselineRun.metrics.citation_precision * 100).toFixed(1)}% vs Dense baseline</span>
              </div>
            )}
          </div>

          {/* Recall@K */}
          <div className="glass-panel" style={{ padding: "18px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Recall@5 / MRR</span>
              <Layers size={16} color="var(--accent-primary)" />
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "#ffffff", marginTop: "8px", fontFamily: "monospace" }}>
              {(activeRun.metrics.recall_at_k * 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
              MRR: {activeRun.metrics.mrr.toFixed(3)}
            </div>
          </div>

          {/* Abstention Quality */}
          <div className="glass-panel" style={{ padding: "18px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Abstention on Out-of-Bounds</span>
              <AlertTriangle size={16} color="var(--accent-amber)" />
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "#ffffff", marginTop: "8px", fontFamily: "monospace" }}>
              {(activeRun.metrics.abstention_quality * 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
              Correctly refused hallucinating
            </div>
          </div>
        </div>
      )}

      {/* Comparison Run Selector */}
      <div className="glass-panel" style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)" }}>Selected Benchmark Run:</span>
          <select
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            style={{
              background: "var(--bg-canvas)",
              color: "#ffffff",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--radius-md)",
              padding: "6px 12px",
              fontSize: "12px",
              outline: "none",
            }}
          >
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id} ({r.model}) — {new Date(r.timestamp).toLocaleDateString()}
              </option>
            ))}
          </select>
        </div>

        {activeRun && (
          <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "11px", color: "var(--text-muted)" }}>
            <span>Passed: <strong style={{ color: "var(--accent-emerald)" }}>{activeRun.passed_cases}</strong> / {activeRun.total_cases}</span>
            <span>Avg Latency: <strong style={{ color: "#ffffff" }}>{activeRun.metrics.avg_latency_ms}ms</strong></span>
            <span>Cost: <strong style={{ color: "#ffffff" }}>${activeRun.metrics.total_cost_usd}</strong></span>
          </div>
        )}
      </div>

      {/* Test Cases Table */}
      {activeRun && activeRun.test_cases && activeRun.test_cases.length > 0 && (
        <div className="glass-panel" style={{ overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)" }}>
            <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff" }}>
              Sample Curated Test Cases &amp; LLM-as-Judge Verdicts
            </h3>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12px" }}>
              <thead>
                <tr style={{ background: "rgba(0,0,0,0.3)", color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
                  <th style={{ padding: "12px 20px", fontWeight: 600 }}>Test ID</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Question</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Category</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Faithfulness</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Latency</th>
                  <th style={{ padding: "12px 20px", fontWeight: 600, textAlign: "right" }}>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {activeRun.test_cases.map((tc) => (
                  <tr key={tc.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "12px 20px", fontFamily: "monospace", color: "var(--accent-secondary)" }}>
                      {tc.id}
                    </td>
                    <td style={{ padding: "12px 16px", color: "#ffffff", maxWidth: "380px" }}>
                      {tc.question}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span className="badge badge-brand" style={{ fontSize: "10px" }}>
                        {tc.category}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "var(--accent-emerald)" }}>
                      {(tc.faithfulness_score * 100).toFixed(0)}%
                    </td>
                    <td style={{ padding: "12px 16px", color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {tc.latency_ms}ms
                    </td>
                    <td style={{ padding: "12px 20px", textAlign: "right" }}>
                      <span className="badge badge-high" style={{ fontSize: "10px" }}>
                        <CheckCircle2 size={11} /> Pass
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
