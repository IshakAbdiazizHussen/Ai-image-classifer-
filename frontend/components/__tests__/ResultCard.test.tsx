import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultCard } from "@/components/ResultCard";
import type { PredictResponse } from "@/lib/api/client";

const sampleResult: PredictResponse = {
  predicted_label: "cat",
  confidence: 0.838,
  probabilities: { cat: 0.838, dog: 0.079 },
  model_version: "20260822T165903Z",
  inference_latency_ms: 30.1,
  cached: false,
};

describe("ResultCard", () => {
  it("renders the predicted label and confidence from the API response", () => {
    render(<ResultCard result={sampleResult} />);

    expect(screen.getByText("cat")).toBeInTheDocument();
    expect(screen.getByText("Confidence: 83.8%")).toBeInTheDocument();
    expect(screen.getByText(/20260822T165903Z/)).toBeInTheDocument();
  });

  it("shows latency when not cached, and a cache indicator when cached", () => {
    const { rerender } = render(<ResultCard result={sampleResult} />);
    expect(screen.getByText(/30 ms/)).toBeInTheDocument();

    rerender(<ResultCard result={{ ...sampleResult, cached: true }} />);
    expect(screen.getByText(/served from cache/)).toBeInTheDocument();
  });
});
