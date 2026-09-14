import EvalDashboard from "@/components/EvalDashboard";

export const metadata = {
  title: "Evaluation Benchmark Suite — AegisAI",
  description: "Faithfulness, citation precision, and retrieval recall metrics.",
};

export default function EvaluationsPage() {
  return <EvalDashboard />;
}
