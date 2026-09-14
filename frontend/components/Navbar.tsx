"use client";

import { usePathname } from "next/navigation";
import { Sparkles, Zap, Shield, HelpCircle } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const getPageTitle = () => {
    if (pathname === "/") return { title: "Knowledge Retrieval & Chat", subtitle: "Evidence-grounded RAG with strict citation verification" };
    if (pathname.startsWith("/documents")) return { title: "Document Ingestion Pipeline", subtitle: "Hierarchical chunking (PDF, DOCX, XLSX, CSV) + Celery workers" };
    if (pathname.startsWith("/traces")) return { title: "Observability & Trace Viewer", subtitle: "End-to-end request pipeline telemetry and latency waterfall" };
    if (pathname.startsWith("/evaluations")) return { title: "Automated Evaluation Engine", subtitle: "Faithfulness, Citation Precision & Recall@K benchmarking" };
    if (pathname.startsWith("/settings")) return { title: "Platform Architecture & Settings", subtitle: "Configure retrieval alpha, rerankers, and prompt versions" };
    return { title: "AegisAI Decision Engine", subtitle: "Enterprise Trust & Grounding" };
  };

  const { title, subtitle } = getPageTitle();

  return (
    <header className="app-header">
      <div>
        <h1 style={{ fontSize: "16px", fontWeight: 700, color: "#ffffff", letterSpacing: "-0.01em" }}>
          {title}
        </h1>
        <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "1px" }}>
          {subtitle}
        </p>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* Active Pipeline Badge */}
        <div 
          style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "7px", 
            padding: "5px 12px", 
            background: "rgba(99, 102, 241, 0.1)", 
            border: "1px solid rgba(99, 102, 241, 0.25)",
            borderRadius: "var(--radius-full)",
            fontSize: "12px",
            color: "#c7d2fe"
          }}
        >
          <Sparkles size={13} color="var(--accent-secondary)" />
          <span style={{ fontWeight: 600 }}>Hybrid RRF</span>
          <span style={{ color: "var(--text-muted)" }}>|</span>
          <span style={{ color: "var(--text-secondary)" }}>BGE-large + BM25</span>
        </div>

        {/* Latency Guarantee Indicator */}
        <div 
          style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "6px", 
            padding: "5px 10px", 
            background: "rgba(16, 185, 129, 0.1)", 
            border: "1px solid rgba(16, 185, 129, 0.25)",
            borderRadius: "var(--radius-full)",
            fontSize: "12px",
            color: "#6ee7b7"
          }}
        >
          <Zap size={13} color="#10b981" />
          <span>p95 &lt; 1.2s</span>
        </div>

        {/* Grounding Shield */}
        <div 
          title="Zero Hallucination Grounding Enforced"
          style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "5px", 
            padding: "5px 10px", 
            background: "rgba(255, 255, 255, 0.05)", 
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-full)",
            fontSize: "12px",
            color: "var(--text-secondary)"
          }}
        >
          <Shield size={13} color="var(--accent-secondary)" />
          <span>Verified</span>
        </div>
      </div>
    </header>
  );
}
