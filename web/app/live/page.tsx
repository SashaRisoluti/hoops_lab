import type { Metadata } from "next";

import { LiveGame } from "@/components/live/LiveGame";
import { PageHeader } from "@/components/PageHeader";

export const metadata: Metadata = {
  title: "Live games",
  description: "Live NBA scores, shots and box scores, loaded in your browser from ESPN.",
  alternates: { canonical: "/live" },
};

export default function LivePage() {
  return (
    <>
      <PageHeader
        title="Live games"
        subtitle="Score, possession, shots and box score for the NBA games of the day."
      />
      <LiveGame />
      <p className="mt-8 text-xs text-ink-faint">
        Live data is loaded by your browser directly from ESPN&apos;s public API. Data: ESPN.
      </p>
    </>
  );
}
