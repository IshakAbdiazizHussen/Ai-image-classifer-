import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProbabilityChart } from "@/components/ProbabilityChart";

describe("ProbabilityChart", () => {
  it("renders one row per class from the API response, sorted by probability", () => {
    render(<ProbabilityChart probabilities={{ airplane: 0.01, cat: 0.84, dog: 0.15 }} />);

    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("cat");
    expect(rows[1]).toHaveTextContent("dog");
    expect(rows[2]).toHaveTextContent("airplane");
    expect(screen.getByText("84.0%")).toBeInTheDocument();
  });

  it("derives the class list entirely from props, not a hardcoded list", () => {
    render(<ProbabilityChart probabilities={{ zebra: 1.0 }} />);
    expect(screen.getByText("zebra")).toBeInTheDocument();
  });
});
