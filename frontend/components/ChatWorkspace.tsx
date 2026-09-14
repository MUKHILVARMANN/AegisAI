"use client";

import { useState } from "react";
import Link from "next/link";
import { 
  Send, 
  Sparkles, 
  ThumbsUp, 
  ThumbsDown, 
  ExternalLink, 
  ShieldCheck, 
  Clock, 
  Cpu, 
  AlertTriangle, 
  BookOpen, 
  ArrowRight,
  Info
} from "lucide-react";
import { api, ChatResponse, Citation } from "@/lib/api";
import CitationCard from "./CitationCard";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  responseMeta?: ChatResponse;
  userRating?: 1 | -1;
}

const SAMPLE_QUESTIONS = [
  { label: "SOC 2 Audit Log Retention", query: "What is the mandatory data retention period for audit logs under SOC2 Section 4.1?" },
  { label: "Q3 Regional Net Margin Delta", query: "Calculate the net margin delta between North America and EMEA for Q3 2024." },
  { label: "Redis Sentinel Failover", query: "Detail the high-availability failover steps when Redis Sentinel reaches quorum timeout." },
  { label: "GDPR EU Sub-processors", query: "List all third-party sub-processors used for customer telemetry ingestion in EU region." },
];

export default function ChatWorkspace() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCitationIndex, setActiveCitationIndex] = useState<number | null>(null);

  // Initial rich message for immediate demonstration
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content: `Welcome to **AegisAI** — Enterprise Trusted Knowledge & Decision Platform.\n\nEvery response is generated via **Hybrid Search (pgvector Dense + BM25)**, cross-encoder reranking, and **strict deterministic citation validation**. Hallucinations are actively intercepted before answers reach the UI.\n\nTry asking a question about compliance, financial models, or technical runbooks below.`,
    },
  ]);

  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [activeRequestMeta, setActiveRequestMeta] = useState<ChatResponse | null>(null);

  const handleSubmit = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const promptText = customQuery || query;
    if (!promptText.trim() || loading) return;

    const userMsgId = `user-${Date.now()}`;
    const newMsg: Message = { id: userMsgId, role: "user", content: promptText };

    setMessages((prev) => [...prev, newMsg]);
    setQuery("");
    setLoading(true);
    setActiveCitationIndex(null);

    try {
      const resp = await api.sendChat({ query: promptText });
      const assistantMsg: Message = {
        id: resp.request_id,
        role: "assistant",
        content: resp.answer,
        responseMeta: resp,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setActiveCitations(resp.citations || []);
      setActiveRequestMeta(resp);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: "An error occurred while communicating with the retrieval engine. Please ensure the backend is running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (requestId: string, rating: 1 | -1) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === requestId ? { ...m, userRating: rating } : m))
    );
    await api.submitFeedback({ request_id: requestId, rating });
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: "24px", height: "calc(100vh - var(--header-height) - 48px)" }}>
      {/* ─── Main Chat Pane ────────────────────────────────────────────────── */}
      <div 
        className="glass-panel" 
        style={{ 
          display: "flex", 
          flexDirection: "column", 
          overflow: "hidden", 
          border: "1px solid var(--border-subtle)" 
        }}
      >
        {/* Messages Stream */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
          {messages.map((msg) => {
            const isUser = msg.role === "user";
            const meta = msg.responseMeta;

            return (
              <div
                key={msg.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignSelf: isUser ? "flex-end" : "flex-start",
                  maxWidth: isUser ? "75%" : "92%",
                }}
              >
                {/* Role / Author Header */}
                <div 
                  style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    gap: "8px", 
                    marginBottom: "6px",
                    alignSelf: isUser ? "flex-end" : "flex-start" 
                  }}
                >
                  {!isUser && (
                    <div 
                      style={{ 
                        width: "18px", 
                        height: "18px", 
                        borderRadius: "50%", 
                        background: "var(--grad-brand)", 
                        display: "flex", 
                        alignItems: "center", 
                        justifyContent: "center" 
                      }}
                    >
                      <Sparkles size={11} color="#ffffff" />
                    </div>
                  )}
                  <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    {isUser ? "You" : "AegisAI Decision Engine"}
                  </span>

                  {meta && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginLeft: "4px" }}>
                      <span className="badge badge-brand" style={{ fontSize: "10px", padding: "2px 6px" }}>
                        {meta.route_taken}
                      </span>
                      <span style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "3px" }}>
                        <Clock size={11} /> {meta.latency_ms}ms
                      </span>
                    </div>
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  style={{
                    padding: "16px 20px",
                    borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                    background: isUser ? "var(--accent-primary)" : "rgba(20, 27, 41, 0.8)",
                    border: isUser ? "none" : "1px solid var(--border-subtle)",
                    color: "#ffffff",
                    fontSize: "14px",
                    lineHeight: 1.65,
                    boxShadow: isUser ? "0 4px 14px rgba(99, 102, 241, 0.3)" : "none",
                  }}
                >
                  <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>

                  {/* Confidence & Limitations Box */}
                  {meta && (
                    <div style={{ marginTop: "14px", paddingTop: "12px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span 
                            className={`badge ${
                              meta.confidence === "high" ? "badge-high" : meta.confidence === "medium" ? "badge-medium" : "badge-low"
                            }`}
                          >
                            <ShieldCheck size={12} />
                            {meta.confidence} Confidence Grounding
                          </span>
                        </div>

                        {/* Thumbs Up / Down feedback */}
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <button
                            onClick={() => handleFeedback(meta.request_id, 1)}
                            className="btn btn-ghost"
                            style={{
                              padding: "4px 8px",
                              color: msg.userRating === 1 ? "var(--accent-emerald)" : "var(--text-muted)",
                              background: msg.userRating === 1 ? "rgba(16, 185, 129, 0.15)" : "transparent",
                            }}
                            title="Helpful and supported"
                          >
                            <ThumbsUp size={13} />
                          </button>
                          <button
                            onClick={() => handleFeedback(meta.request_id, -1)}
                            className="btn btn-ghost"
                            style={{
                              padding: "4px 8px",
                              color: msg.userRating === -1 ? "var(--accent-rose)" : "var(--text-muted)",
                              background: msg.userRating === -1 ? "rgba(244, 63, 94, 0.15)" : "transparent",
                            }}
                            title="Unsupported or inaccurate"
                          >
                            <ThumbsDown size={13} />
                          </button>

                          <Link
                            href={`/traces/${meta.request_id}`}
                            className="btn btn-secondary"
                            style={{ padding: "4px 10px", fontSize: "11px", gap: "4px" }}
                          >
                            <span>Trace</span>
                            <ExternalLink size={11} />
                          </Link>
                        </div>
                      </div>

                      {meta.limitations && meta.limitations.length > 0 && (
                        <div 
                          style={{ 
                            display: "flex", 
                            alignItems: "center", 
                            gap: "6px", 
                            marginTop: "8px", 
                            fontSize: "11px", 
                            color: "var(--text-muted)" 
                          }}
                        >
                          <Info size={12} color="var(--accent-amber)" />
                          <span>Limitations: {meta.limitations.join("; ")}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--text-secondary)", fontSize: "13px" }}>
              <div 
                className="spin-animation" 
                style={{ width: "16px", height: "16px", border: "2px solid var(--accent-primary)", borderTopColor: "transparent", borderRadius: "50%" }} 
              />
              <span>Hybrid retrieval &amp; reranking evidence chunks...</span>
            </div>
          )}
        </div>

        {/* Suggestion Prompts */}
        <div style={{ padding: "8px 24px", display: "flex", gap: "8px", overflowX: "auto", borderTop: "1px solid var(--border-subtle)", background: "rgba(0,0,0,0.2)" }}>
          {SAMPLE_QUESTIONS.map((q) => (
            <button
              key={q.label}
              onClick={() => handleSubmit(undefined, q.query)}
              disabled={loading}
              style={{
                whiteSpace: "nowrap",
                fontSize: "11px",
                padding: "6px 12px",
                borderRadius: "var(--radius-full)",
                background: "rgba(255, 255, 255, 0.04)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-secondary)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--border-accent)";
                e.currentTarget.style.color = "#ffffff";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border-subtle)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              {q.label}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <form 
          onSubmit={(e) => handleSubmit(e)} 
          style={{ 
            padding: "16px 24px", 
            borderTop: "1px solid var(--border-subtle)", 
            display: "flex", 
            gap: "12px", 
            alignItems: "center" 
          }}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question across indexed documents, financial sheets, and policies..."
            disabled={loading}
            style={{
              flex: 1,
              padding: "12px 18px",
              background: "rgba(10, 14, 23, 0.9)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              color: "#ffffff",
              fontSize: "13px",
              outline: "none",
              boxShadow: "inset 0 2px 4px rgba(0,0,0,0.4)",
            }}
            onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-primary)")}
            onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
          />

          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="btn btn-primary"
            style={{ padding: "12px 20px" }}
          >
            <Send size={15} />
            <span>Submit</span>
          </button>
        </form>
      </div>

      {/* ─── Right Citations & Evidence Inspector ─────────────────────────── */}
      <div 
        className="glass-panel" 
        style={{ 
          display: "flex", 
          flexDirection: "column", 
          overflow: "hidden", 
          border: "1px solid var(--border-subtle)" 
        }}
      >
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <BookOpen size={16} color="var(--accent-secondary)" />
            <h2 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff" }}>Evidence Citations</h2>
          </div>
          <span className="badge badge-brand" style={{ fontSize: "10px" }}>
            {activeCitations.length} Citations
          </span>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
          {activeCitations.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 16px", color: "var(--text-muted)" }}>
              <ShieldCheck size={32} color="var(--border-strong)" style={{ margin: "0 auto 12px" }} />
              <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>
                No active evidence yet
              </p>
              <p style={{ fontSize: "11px", marginTop: "4px" }}>
                Submit a query to inspect the reranked chunks and grounded source documents.
              </p>
            </div>
          ) : (
            activeCitations.map((cit, idx) => (
              <CitationCard
                key={cit.chunk_id || idx}
                citation={cit}
                index={idx}
                isActive={activeCitationIndex === idx}
                onSelect={() => setActiveCitationIndex(idx)}
              />
            ))
          )}
        </div>

        {/* Trace Inspector Teaser in Footer */}
        {activeRequestMeta && (
          <div style={{ padding: "14px 16px", borderTop: "1px solid var(--border-subtle)", background: "rgba(0,0,0,0.3)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Pipeline Request ID:</span>
              <span style={{ fontSize: "11px", fontFamily: "monospace", color: "var(--accent-secondary)" }}>
                {activeRequestMeta.request_id}
              </span>
            </div>

            <Link
              href={`/traces/${activeRequestMeta.request_id}`}
              className="btn btn-secondary"
              style={{ width: "100%", justifyContent: "center", fontSize: "12px" }}
            >
              <span>View Full Pipeline Trace</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
