"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  MessageSquare, 
  Files, 
  Activity, 
  BarChart3, 
  Settings, 
  ShieldCheck, 
  Cpu, 
  ExternalLink 
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Chat & Grounding", href: "/", icon: MessageSquare },
  { name: "Document Ingestion", href: "/documents", icon: Files },
  { name: "Traces & Observability", href: "/traces/demo-trace", icon: Activity },
  { name: "Evaluation Engine", href: "/evaluations", icon: BarChart3 },
  { name: "System Config", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="app-sidebar">
      {/* Brand Header */}
      <div style={{ padding: "20px 20px 16px 20px", borderBottom: "1px solid var(--border-subtle)" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div 
            style={{ 
              width: "36px", 
              height: "36px", 
              borderRadius: "10px", 
              background: "var(--grad-brand)", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center",
              boxShadow: "0 0 16px rgba(99, 102, 241, 0.4)"
            }}
          >
            <ShieldCheck size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "17px", fontWeight: 800, letterSpacing: "-0.02em", color: "#ffffff" }}>
                Aegis<span style={{ color: "var(--accent-secondary)" }}>AI</span>
              </span>
              <span className="badge badge-cyan" style={{ fontSize: "9px", padding: "1px 5px" }}>v1.0</span>
            </div>
            <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "1px" }}>
              Enterprise Decision Platform
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav style={{ flex: 1, padding: "16px 12px", display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", padding: "4px 10px 8px" }}>
          Platform Core
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href.split("/")[1] ? `/${item.href.split("/")[1]}` : item.href);

          return (
            <Link
              key={item.name}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                fontSize: "13px",
                fontWeight: isActive ? 600 : 500,
                color: isActive ? "#ffffff" : "var(--text-secondary)",
                backgroundColor: isActive ? "rgba(99, 102, 241, 0.14)" : "transparent",
                border: isActive ? "1px solid rgba(99, 102, 241, 0.28)" : "1px solid transparent",
                transition: "all 0.15s ease",
              }}
            >
              <Icon size={18} color={isActive ? "var(--accent-secondary)" : "var(--text-muted)"} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* System Status Footprint */}
      <div style={{ padding: "16px", borderTop: "1px solid var(--border-subtle)", background: "rgba(0,0,0,0.2)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
          <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#10b981", display: "inline-block", boxShadow: "0 0 8px #10b981" }} />
            pgvector + Hybrid RRF
          </span>
          <span style={{ fontSize: "10px", color: "var(--accent-secondary)", fontFamily: "monospace" }}>99.98%</span>
        </div>
        
        <a 
          href="http://localhost:8000/docs" 
          target="_blank" 
          rel="noreferrer"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "8px 10px",
            background: "var(--bg-surface-glass)",
            borderRadius: "var(--radius-sm)",
            fontSize: "11px",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-subtle)"
          }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Cpu size={13} color="var(--accent-primary)" /> FastAPI OpenAPI Docs
          </span>
          <ExternalLink size={12} />
        </a>
      </div>
    </aside>
  );
}
