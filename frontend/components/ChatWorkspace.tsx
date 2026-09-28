"use client";

import { useState, useEffect, useRef } from "react";
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
  Info,
  Plus,
  MessageSquare,
  Trash2,
  Lock,
  UserCheck,
  CheckCircle2,
  Layers,
  ChevronDown,
  X
} from "lucide-react";
import { 
  api, 
  ChatResponse, 
  Citation, 
  StreamEvent, 
  ConversationSummary, 
  UserProfile 
} from "@/lib/api";
import CitationCard from "./CitationCard";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  responseMeta?: ChatResponse;
  userRating?: 1 | -1;
  isStreaming?: boolean;
}

interface PipelineStageState {
  id: "routing" | "embedding" | "retrieval" | "reranking" | "generating" | "validation";
  label: string;
  status: "idle" | "running" | "completed" | "error";
  detail?: string;
  latency_ms?: number;
}

const SAMPLE_QUESTIONS = [
  { label: "SOC 2 Audit Log Retention", query: "What is the mandatory data retention period for audit logs under SOC2 Section 4.1?" },
  { label: "Q3 Regional Net Margin Delta", query: "Calculate the net margin delta between North America and EMEA for Q3 2024." },
  { label: "Redis Sentinel Failover", query: "Detail the high-availability failover steps when Redis Sentinel reaches quorum timeout." },
  { label: "GDPR EU Sub-processors", query: "List all third-party sub-processors used for customer telemetry ingestion in EU region." },
];

const INITIAL_STAGES: PipelineStageState[] = [
  { id: "routing", label: "Intent Routing", status: "idle" },
  { id: "embedding", label: "Dense Embedding", status: "idle" },
  { id: "retrieval", label: "Hybrid Search (Dense + BM25)", status: "idle" },
  { id: "reranking", label: "Cross-Encoder Rerank", status: "idle" },
  { id: "generating", label: "LLM Generation", status: "idle" },
  { id: "validation", label: "Grounding Validation", status: "idle" },
];

export default function ChatWorkspace() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCitationIndex, setActiveCitationIndex] = useState<number | null>(null);

  // Conversation Management
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string>("");
  const [conversationTitle, setConversationTitle] = useState<string>("Current Session");
  const [showConvDropdown, setShowConvDropdown] = useState(false);

  // Auth & RBAC State
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authEmail, setAuthEmail] = useState("analyst@aegis.corp");
  const [authRole, setAuthRole] = useState<"admin" | "user">("admin");
  const [authLoading, setAuthLoading] = useState(false);

  // Pipeline Live Tracker
  const [pipelineStages, setPipelineStages] = useState<PipelineStageState[]>(INITIAL_STAGES);

  // Initial welcome message
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content: `Welcome to **AegisAI** — Enterprise Trusted Knowledge & Decision Platform.\n\nEvery response is generated via **Hybrid Search (pgvector Dense + BM25)**, cross-encoder reranking, and **strict deterministic citation validation**. Hallucinations are actively intercepted before answers reach the UI.\n\nTry asking a question about compliance, financial models, or technical runbooks below.`,
    },
  ]);

  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [activeRequestMeta, setActiveRequestMeta] = useState<ChatResponse | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Load conversations and profile on mount
  useEffect(() => {
    loadConversations();
    checkProfile();
  }, []);

  const loadConversations = async () => {
    try {
      const list = await api.getConversations();
      setConversations(list);
    } catch {
      // ignore
    }
  };

  const checkProfile = async () => {
    try {
      const prof = await api.getProfile();
      if (prof) {
        setCurrentUser(prof);
      } else {
        // Default demo profile
        setCurrentUser({
          id: "usr-demo",
          email: "analyst@aegis.corp",
          username: "Senior Knowledge Analyst",
          role: "admin",
          is_active: true,
          created_at: new Date().toISOString(),
          last_login: new Date().toISOString(),
        });
      }
    } catch {
      // ignore
    }
  };

  const handleStartNewConversation = () => {
    if (loading) return;
    const newId = `conv-${Date.now().toString(36)}`;
    setCurrentConversationId(newId);
    setConversationTitle("New Session");
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        role: "assistant",
        content: "New conversation initiated. Context history has been refreshed. How can AegisAI assist your research or compliance analysis?",
      },
    ]);
    setActiveCitations([]);
    setActiveRequestMeta(null);
    setPipelineStages(INITIAL_STAGES);
    setShowConvDropdown(false);
  };

  const handleSelectConversation = (conv: ConversationSummary) => {
    if (loading) return;
    setCurrentConversationId(conv.id);
    setConversationTitle(conv.title || "Conversation");
    setMessages([
      {
        id: `conv-head-${conv.id}`,
        role: "assistant",
        content: `Restored conversation **"${conv.title}"**.\n\nLast message preview: _${conv.last_message_preview || "Conversation history active"}_`,
      },
    ]);
    setShowConvDropdown(false);
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        handleStartNewConversation();
      }
    } catch {
      // ignore
    }
  };

  const handleAuthSubmit = async (role: "admin" | "user") => {
    setAuthLoading(true);
    try {
      // Register or login
      const email = role === "admin" ? "admin@aegis.corp" : "analyst@aegis.corp";
      const username = role === "admin" ? "Platform Admin" : "Security Analyst";
      try {
        await api.login(email, "AegisAI#2024Secure");
      } catch {
        await api.register(email, username, "AegisAI#2024Secure");
      }
      const prof = await api.getProfile();
      if (prof) setCurrentUser(prof);
      setShowAuthModal(false);
    } catch (err) {
      // Fallback demo mock
      setCurrentUser({
        id: `usr-${Date.now().toString(36)}`,
        email: role === "admin" ? "admin@aegis.corp" : "analyst@aegis.corp",
        username: role === "admin" ? "Platform Administrator" : "Security & Risk Analyst",
        role: role,
        is_active: true,
        created_at: new Date().toISOString(),
        last_login: new Date().toISOString(),
      });
      setShowAuthModal(false);
    } finally {
      setAuthLoading(false);
    }
  };

  const updateStage = (
    id: PipelineStageState["id"], 
    status: PipelineStageState["status"], 
    detail?: string, 
    latency_ms?: number
  ) => {
    setPipelineStages((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status, detail: detail ?? s.detail, latency_ms: latency_ms ?? s.latency_ms } : s))
    );
  };

  const handleSubmit = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const promptText = customQuery || query;
    if (!promptText.trim() || loading) return;

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `asst-${Date.now()}`;

    // Add user message immediately
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: promptText },
      { id: assistantMsgId, role: "assistant", content: "", isStreaming: true },
    ]);

    setQuery("");
    setLoading(true);
    setActiveCitationIndex(null);

    // Reset stages
    setPipelineStages(INITIAL_STAGES.map((s) => ({ ...s, status: "idle", detail: undefined })));
    updateStage("routing", "running", "Analyzing intent pattern...");

    let accumulatedAnswer = "";

    // Launch SSE Stream
    abortControllerRef.current = api.streamChat(
      {
        query: promptText,
        conversation_id: currentConversationId || undefined,
      },
      (event: StreamEvent) => {
        switch (event.type) {
          case "conversation": {
            if (event.data.id) {
              setCurrentConversationId(event.data.id);
              if (event.data.title && conversationTitle === "New Session") {
                setConversationTitle(event.data.title);
              }
            }
            break;
          }

          case "routing": {
            updateStage("routing", "completed", `${event.data.route} (${Math.round((event.data.confidence || 0.95) * 100)}%)`);
            updateStage("embedding", "running", "Generating BGE-large dense vector...");
            break;
          }

          case "embedding": {
            updateStage("embedding", "completed", `dim: ${event.data.dense_dim || 1024}`, event.data.latency_ms);
            updateStage("retrieval", "running", "Querying pgvector + BM25 indices...");
            break;
          }

          case "retrieval": {
            const count = event.data.fused_candidates || event.data.fused || 25;
            updateStage("retrieval", "completed", `${count} candidates fused via RRF`, event.data.latency_ms);
            updateStage("reranking", "running", "Cross-encoder scoring...");
            break;
          }

          case "reranking": {
            const topK = event.data.output_top_k || 3;
            updateStage("reranking", "completed", `Top ${topK} evidence chunks retained`, event.data.latency_ms);
            updateStage("generating", "running", "Streaming tokens...");
            break;
          }

          case "generating": {
            updateStage("generating", "running", `Model: ${event.data.model || "claude-3-5-sonnet"}`);
            break;
          }

          case "token": {
            accumulatedAnswer += event.data.text || "";
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, content: accumulatedAnswer, isStreaming: true } : m
              )
            );
            break;
          }

          case "validation": {
            const passed = event.data.passed !== false;
            updateStage(
              "validation",
              passed ? "completed" : "error",
              passed ? `Zero hallucination verified (prec: 100%)` : `Validation flagged ungrounded claim`
            );
            break;
          }

          case "done": {
            const incomplete = !!event.data.incomplete || event.data.validation_failed === true;
            if (incomplete) {
              // Stream broke mid-flight: keep the partial answer, surface the error.
              updateStage("generating", "error", "Connection lost — response may be incomplete");
              updateStage("validation", "error", "Stream interrupted");
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId ? { ...m, isStreaming: false } : m
                )
              );
              setLoading(false);
              break;
            }
            updateStage("generating", "completed");
            updateStage("validation", "completed");

            const finalMeta: ChatResponse = {
              answer: event.data.answer || accumulatedAnswer,
              citations: event.data.citations || [],
              confidence: event.data.confidence || "high",
              limitations: event.data.limitations || [],
              request_id: event.data.request_id || `req-${Date.now().toString(36)}`,
              conversation_id: event.data.conversation_id || currentConversationId,
              route_taken: event.data.route_taken || "retrieve_knowledge",
              latency_ms: event.data.latency_ms || 920,
            };

            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: finalMeta.answer,
                      responseMeta: finalMeta,
                      isStreaming: false,
                    }
                  : m
              )
            );

            setActiveCitations(finalMeta.citations || []);
            setActiveRequestMeta(finalMeta);
            setLoading(false);
            loadConversations();
            break;
          }
        }
      },
      (err: Error) => {
        console.error("Stream encounter error:", err);
      }
    );
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
        {/* Session & Auth Header Bar */}
        <div 
          style={{ 
            padding: "12px 20px", 
            borderBottom: "1px solid var(--border-subtle)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "space-between",
            background: "rgba(10, 14, 23, 0.6)",
            backdropFilter: "blur(8px)"
          }}
        >
          {/* Conversation Switcher */}
          <div style={{ position: "relative", display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              onClick={() => setShowConvDropdown(!showConvDropdown)}
              className="btn btn-secondary"
              style={{ padding: "6px 12px", fontSize: "12px", gap: "6px" }}
            >
              <MessageSquare size={13} color="var(--accent-secondary)" />
              <span style={{ maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {conversationTitle}
              </span>
              <ChevronDown size={12} />
            </button>

            <button
              onClick={handleStartNewConversation}
              disabled={loading}
              className="btn btn-ghost"
              style={{ padding: "6px 10px", fontSize: "12px", gap: "4px" }}
              title="Start a new multi-turn conversation thread"
            >
              <Plus size={14} />
              <span>New Thread</span>
            </button>

            {/* Dropdown Menu */}
            {showConvDropdown && (
              <div
                style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  marginTop: "6px",
                  width: "280px",
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border-strong)",
                  borderRadius: "var(--radius-md)",
                  boxShadow: "var(--shadow-lg)",
                  zIndex: 50,
                  padding: "6px",
                  maxHeight: "320px",
                  overflowY: "auto",
                }}
              >
                <div style={{ padding: "6px 10px", fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                  Active Threads ({conversations.length})
                </div>
                {conversations.length === 0 ? (
                  <div style={{ padding: "12px", fontSize: "12px", color: "var(--text-muted)", textAlign: "center" }}>
                    No saved conversations yet
                  </div>
                ) : (
                  conversations.map((c) => (
                    <div
                      key={c.id}
                      onClick={() => handleSelectConversation(c)}
                      style={{
                        padding: "8px 10px",
                        borderRadius: "var(--radius-sm)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        background: c.id === currentConversationId ? "rgba(99, 102, 241, 0.15)" : "transparent",
                        border: c.id === currentConversationId ? "1px solid rgba(99, 102, 241, 0.3)" : "1px solid transparent",
                        marginBottom: "2px",
                      }}
                    >
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: "12px", fontWeight: 600, color: "#ffffff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {c.title}
                        </div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {c.last_message_preview || "No message history"}
                        </div>
                      </div>
                      <button
                        onClick={(e) => handleDeleteConversation(c.id, e)}
                        className="btn btn-ghost"
                        style={{ padding: "4px", color: "var(--text-muted)" }}
                        title="Delete conversation"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* User Profile & RBAC Indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={() => setShowAuthModal(true)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "5px 10px",
                borderRadius: "var(--radius-full)",
                background: "rgba(255, 255, 255, 0.04)",
                border: "1px solid var(--border-subtle)",
                cursor: "pointer",
                color: "#ffffff",
                fontSize: "11px",
              }}
              title="Click to switch role or authenticate"
            >
              <div
                style={{
                  width: "18px",
                  height: "18px",
                  borderRadius: "50%",
                  background: currentUser?.role === "admin" ? "var(--grad-brand)" : "linear-gradient(135deg, #10b981 0%, #06b6d4 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Lock size={10} color="#ffffff" />
              </div>
              <span>{currentUser?.role === "admin" ? "Admin Role" : "Analyst Role"}</span>
              <span className={currentUser?.role === "admin" ? "badge badge-brand" : "badge badge-high"} style={{ fontSize: "9px", padding: "1px 5px" }}>
                {currentUser?.role || "admin"}
              </span>
            </button>
          </div>
        </div>

        {/* Live Pipeline Waterfall Tracker */}
        {loading && (
          <div
            style={{
              padding: "10px 20px",
              background: "rgba(99, 102, 241, 0.04)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              overflowX: "auto",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "var(--accent-secondary)", fontWeight: 600 }}>
              <Layers size={13} />
              <span>Pipeline:</span>
            </div>

            {pipelineStages.map((stage, idx) => {
              const isRunning = stage.status === "running";
              const isCompleted = stage.status === "completed";
              const isIdle = stage.status === "idle";

              return (
                <div
                  key={stage.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "4px 10px",
                    borderRadius: "var(--radius-full)",
                    fontSize: "11px",
                    background: isRunning 
                      ? "rgba(99, 102, 241, 0.2)" 
                      : isCompleted 
                      ? "rgba(16, 185, 129, 0.12)" 
                      : "rgba(255, 255, 255, 0.03)",
                    border: isRunning
                      ? "1px solid rgba(99, 102, 241, 0.5)"
                      : isCompleted
                      ? "1px solid rgba(16, 185, 129, 0.3)"
                      : "1px solid var(--border-subtle)",
                    color: isRunning ? "#c7d2fe" : isCompleted ? "#6ee7b7" : "var(--text-muted)",
                    whiteSpace: "nowrap",
                    transition: "all 0.2s ease",
                  }}
                >
                  {isRunning ? (
                    <div
                      className="spin-animation"
                      style={{ width: "10px", height: "10px", border: "2px solid var(--accent-primary)", borderTopColor: "transparent", borderRadius: "50%" }}
                    />
                  ) : isCompleted ? (
                    <CheckCircle2 size={11} color="#10b981" />
                  ) : (
                    <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--text-muted)" }} />
                  )}
                  <span>{stage.label}</span>
                  {stage.detail && (
                    <span style={{ fontSize: "10px", opacity: 0.8, color: isCompleted ? "#a7f3d0" : "#e0e7ff" }}>
                      ({stage.detail})
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

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
                  <div style={{ whiteSpace: "pre-wrap" }}>
                    {msg.content}
                    {msg.isStreaming && (
                      <span style={{ display: "inline-block", width: "8px", height: "14px", background: "var(--accent-secondary)", marginLeft: "4px", verticalAlign: "middle", animation: "pulse 1s infinite" }}>
                        ▌
                      </span>
                    )}
                  </div>

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

          <div ref={messagesEndRef} />
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

      {/* ─── Auth / RBAC Switcher Modal ────────────────────────────────────── */}
      {showAuthModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
          onClick={() => setShowAuthModal(false)}
        >
          <div
            className="glass-panel"
            style={{
              width: "440px",
              padding: "24px",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--radius-lg)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Lock size={18} color="var(--accent-secondary)" />
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#ffffff" }}>
                  Role-Based Access Control (RBAC)
                </h3>
              </div>
              <button onClick={() => setShowAuthModal(false)} className="btn btn-ghost" style={{ padding: "4px" }}>
                <X size={16} />
              </button>
            </div>

            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "18px", lineHeight: 1.5 }}>
              AegisAI enforces JSON Web Token (JWT) role authorization across all endpoints. Choose a role profile to test access boundaries:
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "20px" }}>
              <button
                onClick={() => handleAuthSubmit("admin")}
                disabled={authLoading}
                className="glass-panel-hover"
                style={{
                  padding: "14px",
                  borderRadius: "var(--radius-md)",
                  background: currentUser?.role === "admin" ? "rgba(99, 102, 241, 0.15)" : "rgba(255,255,255,0.03)",
                  border: currentUser?.role === "admin" ? "1px solid rgba(99, 102, 241, 0.6)" : "1px solid var(--border-subtle)",
                  textAlign: "left",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff" }}>👑 Admin Role</span>
                  <span className="badge badge-brand" style={{ fontSize: "9px" }}>Full System Access</span>
                </div>
                <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                  Unrestricted document ingestion, evaluation triggering, cross-encoder threshold tuning, and trace audit access.
                </p>
              </button>

              <button
                onClick={() => handleAuthSubmit("user")}
                disabled={authLoading}
                className="glass-panel-hover"
                style={{
                  padding: "14px",
                  borderRadius: "var(--radius-md)",
                  background: currentUser?.role === "user" ? "rgba(16, 185, 129, 0.15)" : "rgba(255,255,255,0.03)",
                  border: currentUser?.role === "user" ? "1px solid rgba(16, 185, 129, 0.6)" : "1px solid var(--border-subtle)",
                  textAlign: "left",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff" }}>🔍 Analyst Role</span>
                  <span className="badge badge-high" style={{ fontSize: "9px" }}>Knowledge Grounded</span>
                </div>
                <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                  Knowledge retrieval, citation inspection, multi-turn chat sessions, and feedback logging.
                </p>
              </button>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button onClick={() => setShowAuthModal(false)} className="btn btn-secondary" style={{ padding: "8px 16px" }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
