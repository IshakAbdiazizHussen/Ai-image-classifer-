import type { PredictionHistoryItem } from "@/lib/api/client";

export function HistoryTable({ items }: { items: PredictionHistoryItem[] }) {
  if (items.length === 0) {
    return <p>No predictions yet.</p>;
  }

  return (
    <table className="history-table">
      <thead>
        <tr>
          <th>Predicted label</th>
          <th>Confidence</th>
          <th>Model version</th>
          <th>When</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <td>{item.predicted_label}</td>
            <td>{(item.confidence * 100).toFixed(1)}%</td>
            <td>{item.model_version}</td>
            <td>{new Date(item.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
