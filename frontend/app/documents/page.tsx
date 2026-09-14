import DocumentUpload from "@/components/DocumentUpload";

export const metadata = {
  title: "Document Ingestion — AegisAI",
  description: "Hierarchical document parsing, passage chunking, and pgvector embeddings.",
};

export default function DocumentsPage() {
  return <DocumentUpload />;
}
