import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UploadForm } from "@/components/UploadForm";
import type { PredictResponse } from "@/lib/api/client";

function makeFile(name: string, type: string, sizeBytes = 1024): File {
  return new File([new Uint8Array(sizeBytes)], name, { type });
}

const samplePrediction: PredictResponse = {
  predicted_label: "cat",
  confidence: 0.9,
  probabilities: { cat: 0.9 },
  model_version: "v1",
  inference_latency_ms: 10,
  cached: false,
};

describe("UploadForm", () => {
  it("surfaces a server-side validation error rather than swallowing it", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockRejectedValue(new Error("Unsupported file type 'text/plain'."));
    const onPredicted = vi.fn();

    render(<UploadForm onSubmit={onSubmit} onPredicted={onPredicted} />);

    await user.upload(screen.getByLabelText(/choose an image/i), makeFile("cat.png", "image/png"));
    await user.click(screen.getByRole("button", { name: /classify image/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Unsupported file type 'text/plain'."
      );
    });
    expect(onPredicted).not.toHaveBeenCalled();
  });

  it("rejects an unsupported file type client-side without calling onSubmit", async () => {
    // applyAccept: false — a real browser mostly enforces the input's
    // `accept` filter, but it's not guaranteed (drag-and-drop, older
    // browsers), so the component re-validates itself. Bypass user-event's
    // accept filtering here to exercise that defense-in-depth check.
    const user = userEvent.setup({ applyAccept: false });
    const onSubmit = vi.fn();

    render(<UploadForm onSubmit={onSubmit} onPredicted={vi.fn()} />);
    await user.upload(screen.getByLabelText(/choose an image/i), makeFile("notes.txt", "text/plain"));

    expect(screen.getByRole("alert")).toHaveTextContent(/unsupported file type/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit and onPredicted on a successful classification", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(samplePrediction);
    const onPredicted = vi.fn();

    render(<UploadForm onSubmit={onSubmit} onPredicted={onPredicted} />);
    await user.upload(screen.getByLabelText(/choose an image/i), makeFile("cat.png", "image/png"));
    await user.click(screen.getByRole("button", { name: /classify image/i }));

    await waitFor(() => expect(onPredicted).toHaveBeenCalledWith(samplePrediction));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
