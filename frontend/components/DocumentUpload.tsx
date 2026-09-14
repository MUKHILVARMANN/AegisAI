"use client";

import { useState, useEffect, useRef } from "react";
import { 
  UploadCloud, 
  FileText, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Layers, 
  FileSpreadsheet,
  Database,
  ArrowUpRight
} from "lucide-react";
import { api, DocumentItem } from "@/lib/api";

export default function DocumentUpload() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (e) {
      console.error("Failed to load documents:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const newDoc = await api.uploadDocument(file);
        setDocuments((prev) => [newDoc, ...prev]);
      } catch (err) {
        console.error("Upload error:", err);
      }
    }

    setUploading(false);
  };

  const handleReprocess = async (docId: string) => {
    try {
      await api.reprocessDocument(docId);
      setDocuments((prev) =>
        prev.map((d) => (d.id === docId ? { ...d, status: "processing" } : d))
      );
      setTimeout(() => {
        setDocuments((prev) =>
          prev.map((d) => (d.id === docId ? { ...d, status: "indexed" } : d))
        );
      }, 2500);
    } catch (e) {
      console.error("Reprocess error:", e);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const getStatusBadge = (status: DocumentItem["status"]) => {
    switch (status) {
      case "indexed":
        return (
          <span className="badge badge-high">
            <CheckCircle2 size={11} /> Indexed
          </span>
        );
      case "processing":
        return (
          <span className="badge badge-medium">
            <RefreshCw size={11} className="spin-animation" /> Processing
          </span>
        );
      case "failed":
        return (
          <span className="badge badge-low">
            <AlertCircle size={11} /> Failed
          </span>
        );
      default:
        return (
          <span className="badge badge-brand">
            <Clock size={11} /> Uploaded
          </span>
        );
    }
  };

  const getFormatIcon = (type: string) => {
    if (type === "xlsx" || type === "csv") {
      return <FileSpreadsheet size={18} color="var(--accent-emerald)" />;
    }
    return <FileText size={18} color="var(--accent-secondary)" />;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Banner / Ingestion Pipeline Overview */}
      <div 
        className="glass-panel"
        style={{
          padding: "24px",
          background: "radial-gradient(ellipse at 80% 20%, rgba(99, 102, 241, 0.12) 0%, rgba(15, 20, 29, 0.8) 70%)",
          border: "1px solid var(--border-subtle)"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#ffffff", display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={20} color="var(--accent-secondary)" />
              Enterprise Document Ingestion Engine
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px", maxWidth: "720px", lineHeight: 1.5 }}>
              Files undergo hierarchical parsing, parent-child passage segmentation, table extraction, metadata tagging, and asynchronous indexing with sentence-transformers into pgvector.
            </p>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <div style={{ padding: "10px 14px", background: "rgba(0,0,0,0.3)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", textAlign: "center" }}>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--accent-secondary)", fontFamily: "monospace" }}>
                {documents.length}
              </div>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Documents</div>
            </div>
            <div style={{ padding: "10px 14px", background: "rgba(0,0,0,0.3)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", textAlign: "center" }}>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#ffffff", fontFamily: "monospace" }}>
                {documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0)}
              </div>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Indexed Chunks</div>
            </div>
          </div>
        </div>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? "var(--accent-secondary)" : "var(--border-strong)"}`,
          borderRadius: "var(--radius-lg)",
          padding: "36px 24px",
          textAlign: "center",
          background: dragOver ? "rgba(99, 102, 241, 0.08)" : "rgba(15, 20, 29, 0.4)",
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={(e) => handleFiles(e.target.files)}
          multiple
          accept=".pdf,.docx,.xlsx,.csv"
          style={{ display: "none" }}
        />

        <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "rgba(99, 102, 241, 0.15)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
          <UploadCloud size={24} color="var(--accent-secondary)" />
        </div>

        <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#ffffff" }}>
          {uploading ? "Ingesting and chunking documents..." : "Drop enterprise documents here or click to browse"}
        </h3>
        <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
          Supported formats: PDF (with page & heading extraction), DOCX, XLSX (tables preserved), CSV.
        </p>
      </div>

      {/* Documents Library Table */}
      <div className="glass-panel" style={{ overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff" }}>Indexed Knowledge Repository</h3>
          <button onClick={loadDocuments} className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "11px" }}>
            <RefreshCw size={12} className={loading ? "spin-animation" : ""} /> Refresh
          </button>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12px" }}>
            <thead>
              <tr style={{ background: "rgba(0,0,0,0.3)", color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
                <th style={{ padding: "12px 20px", fontWeight: 600 }}>Document Name</th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>Format</th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>Status</th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>Chunks / Sections</th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>Size</th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>Ingested At</th>
                <th style={{ padding: "12px 20px", fontWeight: 600, textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr 
                  key={doc.id} 
                  style={{ borderBottom: "1px solid var(--border-subtle)", transition: "background 0.15s ease" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <td style={{ padding: "14px 20px", color: "#ffffff", fontWeight: 500, display: "flex", alignItems: "center", gap: "10px" }}>
                    {getFormatIcon(doc.type)}
                    <span style={{ maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={doc.name}>
                      {doc.name}
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <span className="badge badge-brand" style={{ fontSize: "10px" }}>
                      {doc.type.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    {getStatusBadge(doc.status)}
                  </td>
                  <td style={{ padding: "14px 16px", color: "var(--text-secondary)", fontFamily: "monospace" }}>
                    {doc.chunk_count ?? 0} chunks / {doc.section_count ?? 0} sec
                  </td>
                  <td style={{ padding: "14px 16px", color: "var(--text-muted)" }}>
                    {formatBytes(doc.size)}
                  </td>
                  <td style={{ padding: "14px 16px", color: "var(--text-muted)" }}>
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: "14px 20px", textAlign: "right" }}>
                    <button
                      onClick={() => handleReprocess(doc.id)}
                      className="btn btn-secondary"
                      style={{ padding: "4px 8px", fontSize: "11px", gap: "4px" }}
                      title="Trigger full re-chunking and re-indexing"
                    >
                      <RefreshCw size={11} />
                      Reprocess
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
