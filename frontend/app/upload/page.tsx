"use client";

import { useState } from "react";
import { UploadForm } from "@/components/UploadForm";
import { ResultCard } from "@/components/ResultCard";
import { ProbabilityChart } from "@/components/ProbabilityChart";
import { predictImage, type PredictResponse } from "@/lib/api/client";

export default function UploadPage() {
  const [result, setResult] = useState<PredictResponse | null>(null);

  return (
    <main className="page">
      <h1>Classify an image</h1>
      <p className="page-intro">
        Upload a JPEG, PNG, or WebP image to get a predicted class and
        confidence from the served model.
      </p>

      <UploadForm onSubmit={predictImage} onPredicted={setResult} />

      {result && (
        <section className="result-section">
          <ResultCard result={result} />
          <ProbabilityChart probabilities={result.probabilities} />
        </section>
      )}
    </main>
  );
}
