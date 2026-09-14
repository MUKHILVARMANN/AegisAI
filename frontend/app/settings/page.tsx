"use client";

import { useState } from "react";
import { 
  Settings, 
  Sliders, 
  Database, 
  Cpu, 
  ShieldCheck, 
  Save, 
  Check, 
  Layers, 
  FileCode,
  Gauge
} from "lucide-react";

export default function SettingsPage() {
  const [alpha, setAlpha] = useState(0.65);
  const [rrfK, setRrfK] = useState(60);
  const [topNCandidates, setTopNCandidates] = useState(25);
  const [topKReranked, setTopKReranked] = useState(4);
  const [rerankThreshold, setRerankThreshold] = useState(0.75);
  const [selectedModel, setSelectedModel] = useState("claude-3-5-sonnet-20241022");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "900px" }}>
      {/* Header */}
      <div 
        className="glass-panel" 
        style={{ 
          padding: "24px", 
          background: "radial-gradient(ellipse at 80% 20%, rgba(99, 102, 241, 0.12) 0%, rgba(15, 20, 29, 0.8) 70%)" 
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#ffffff", display: "flex", alignItems: "center", gap: "8px" }}>
              <Settings size={20} color="var(--accent-secondary)" />
              Platform Architecture &amp; Retrieval Tuning
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>
              Tune hybrid search weights, reranker thresholds, model parameters, and prompt versioning.
            </p>
          </div>

          <button onClick={handleSave} className="btn btn-primary" style={{ padding: "8px 18px" }}>
            {saved ? <Check size={14} /> : <Save size={14} />}
            <span>{saved ? "Saved Configuration" : "Save Changes"}</span>
          </button>
        </div>
      </div>

      {/* Retrieval Tuning Card */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#ffffff", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Sliders size={18} color="var(--accent-primary)" />
          Hybrid Search &amp; Reciprocal Rank Fusion (RRF)
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Alpha Slider */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <div>
                <span style={{ fontSize: "13px", fontWeight: 600, color: "#ffffff" }}>
                  Dense vs. BM25 Balance (Alpha)
                </span>
                <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  0.0 = Pure BM25 Keyword Search | 1.0 = Pure Dense Vector Similarity
                </p>
              </div>
              <span style={{ fontSize: "14px", fontWeight: 700, fontFamily: "monospace", color: "var(--accent-secondary)" }}>
                {alpha.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={alpha}
              onChange={(e) => setAlpha(parseFloat(e.target.value))}
              style={{ width: "100%", accentColor: "var(--accent-primary)", cursor: "pointer" }}
            />
          </div>

          {/* RRF K Constant */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                RRF Smoothing Constant (k)
              </label>
              <input
                type="number"
                value={rrfK}
                onChange={(e) => setRrfK(parseInt(e.target.value) || 60)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  background: "rgba(0,0,0,0.3)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  color: "#ffffff",
                  fontFamily: "monospace",
                  outline: "none",
                }}
              />
              <span style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
                Recommended benchmark default: 60
              </span>
            </div>

            <div>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                Initial Candidates (Top-N)
              </label>
              <input
                type="number"
                value={topNCandidates}
                onChange={(e) => setTopNCandidates(parseInt(e.target.value) || 20)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  background: "rgba(0,0,0,0.3)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  color: "#ffffff",
                  fontFamily: "monospace",
                  outline: "none",
                }}
              />
              <span style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
                Retrieved chunks sent to cross-encoder reranker
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Reranker & Model Card */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#ffffff", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Cpu size={18} color="var(--accent-secondary)" />
          Cross-Encoder Reranker &amp; Foundation Model
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div>
            <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
              Primary Generation Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                background: "rgba(0,0,0,0.3)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                color: "#ffffff",
                outline: "none",
              }}
            >
              <option value="claude-3-5-sonnet-20241022">Anthropic Claude 3.5 Sonnet (Recommended)</option>
              <option value="gpt-4o">OpenAI GPT-4o</option>
              <option value="gemini-1.5-pro">Google Gemini 1.5 Pro</option>
              <option value="llama-3.3-70b">Meta Llama 3.3 70B (Ollama Local)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
              Final Context Top-K
            </label>
            <input
              type="number"
              value={topKReranked}
              onChange={(e) => setTopKReranked(parseInt(e.target.value) || 4)}
              style={{
                width: "100%",
                padding: "10px 14px",
                background: "rgba(0,0,0,0.3)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                color: "#ffffff",
                fontFamily: "monospace",
                outline: "none",
              }}
            />
          </div>
        </div>

        {/* Prompt Versioning Info */}
        <div style={{ marginTop: "20px", padding: "16px", background: "rgba(0,0,0,0.25)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "#ffffff", display: "flex", alignItems: "center", gap: "6px" }}>
              <FileCode size={14} color="var(--accent-primary)" />
              Active System Prompt: <code style={{ color: "var(--accent-secondary)", marginLeft: "4px" }}>prompt_v2.4_strict_grounding</code>
            </span>
            <span className="badge badge-high" style={{ fontSize: "9px" }}>Production</span>
          </div>
          <p style={{ fontSize: "11px", color: "var(--text-muted)", lineHeight: 1.5 }}>
            Includes mandatory JSON schema output definition, strict citation attribution checks, and deterministic abstention instructions when retrieved evidence scores below 0.75.
          </p>
        </div>
      </div>
    </div>
  );
}
