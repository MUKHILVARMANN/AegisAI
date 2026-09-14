"use client";

import { useState } from "react";
import { FileText, Copy, Check, ExternalLink, Bookmark } from "lucide-react";
import { Citation } from "@/lib/api";

interface CitationCardProps {
  citation: Citation;
  index: number;
  isActive?: boolean;
  onSelect?: () => void;
}

export default function CitationCard({ citation, index, isActive, onSelect }: CitationCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(citation.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getDocTypeIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (ext === "pdf") return "badge-brand";
    if (ext === "xlsx") return "badge-high";
    if (ext === "csv") return "badge-cyan";
    return "badge-medium";
  };

  const scorePct = Math.round((citation.score || 0.88) * 100);

  return (
    <div
      onClick={onSelect}
      className={`glass-panel ${isActive ? "border-active-glow" : ""}`}
      style={{
        padding: "14px",
        cursor: "pointer",
        borderRadius: "var(--radius-md)",
        background: isActive ? "rgba(99, 102, 241, 0.12)" : "rgba(18, 24, 38, 0.6)",
        border: isActive ? "1px solid rgba(99, 102, 241, 0.6)" : "1px solid var(--border-subtle)",
        boxShadow: isActive ? "0 0 16px rgba(99, 102, 241, 0.25)" : "none",
        transition: "all 0.15s ease",
      }}
    >
      {/* Card Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px", marginBottom: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
          <div
            style={{
              width: "22px",
              height: "22px",
              borderRadius: "6px",
              background: "rgba(99, 102, 241, 0.2)",
              color: "var(--accent-secondary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "11px",
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            [{index + 1}]
          </div>

          <div style={{ minWidth: 0 }}>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "#f1f5f9",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                display: "block",
              }}
              title={citation.document_name}
            >
              {citation.document_name}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
          {citation.page !== undefined && (
            <span
              style={{
                fontSize: "10px",
                padding: "2px 6px",
                borderRadius: "4px",
                background: "rgba(255, 255, 255, 0.08)",
                color: "var(--text-secondary)",
                fontFamily: "monospace",
              }}
            >
              p. {citation.page}
            </span>
          )}
          <button
            onClick={handleCopy}
            title="Copy snippet"
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: copied ? "var(--accent-emerald)" : "var(--text-muted)",
              display: "flex",
              alignItems: "center",
              padding: "3px",
            }}
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
          </button>
        </div>
      </div>

      {/* Snippet Content */}
      <p
        style={{
          fontSize: "12px",
          color: "var(--text-secondary)",
          lineHeight: 1.55,
          fontStyle: "italic",
          background: "rgba(0, 0, 0, 0.25)",
          padding: "8px 10px",
          borderRadius: "var(--radius-sm)",
          borderLeft: "3px solid var(--accent-primary)",
          marginBottom: "10px",
        }}
      >
        &ldquo;{citation.snippet}&rdquo;
      </p>

      {/* Score & Chunk Lineage */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "10px", color: "var(--text-muted)" }}>
        <span style={{ fontFamily: "monospace" }}>ID: {citation.chunk_id.slice(0, 14)}...</span>
        
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span>Relevance:</span>
          <div style={{ width: "42px", height: "4px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "2px", overflow: "hidden" }}>
            <div
              style={{
                width: `${scorePct}%`,
                height: "100%",
                background: scorePct > 90 ? "var(--accent-emerald)" : "var(--accent-secondary)",
              }}
            />
          </div>
          <span style={{ color: "var(--accent-secondary)", fontWeight: 600, fontFamily: "monospace" }}>
            {scorePct}%
          </span>
        </div>
      </div>
    </div>
  );
}
