"use client";

import { useEffect, useState } from "react";
import { HistoryTable } from "@/components/HistoryTable";
import { getHistory, type PaginatedHistoryResponse } from "@/lib/api/client";

const PAGE_SIZE = 10;

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PaginatedHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      setLoading(true);
      setError(null);
      try {
        const response = await getHistory(page, PAGE_SIZE);
        if (!cancelled) setData(response);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load history.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <main className="page">
      <h1>Prediction history</h1>

      {loading && <p>Loading…</p>}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}

      {data && !loading && (
        <>
          <HistoryTable items={data.items} />
          <div className="pagination">
            <button onClick={() => setPage((p) => p - 1)} disabled={page <= 1}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages} ({data.total} total)
            </span>
            <button onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages}>
              Next
            </button>
          </div>
        </>
      )}
    </main>
  );
}
