import TraceViewer from "@/components/TraceViewer";

interface TracePageProps {
  params: Promise<{ id: string }>;
}

export const metadata = {
  title: "Request Trace Detail — AegisAI",
  description: "Detailed pipeline waterfall, hybrid search candidates, and latency analysis.",
};

export default async function TracePage({ params }: TracePageProps) {
  const { id } = await params;
  return <TraceViewer requestId={id} />;
}
