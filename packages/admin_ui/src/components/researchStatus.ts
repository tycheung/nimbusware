export type ResearchBrief = {
  review_status?: string;
  status?: string;
};

export function briefReviewStatus(brief: ResearchBrief): string {
  return brief.review_status || brief.status || "unknown";
}

export function isPendingBrief(brief: ResearchBrief): boolean {
  return briefReviewStatus(brief) === "pending";
}
