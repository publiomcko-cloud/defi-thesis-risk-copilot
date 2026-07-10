import { riskTone } from "@/lib/formatting";
import type { RiskRating } from "@/lib/types";

type RiskRatingCardProps = {
  rating: RiskRating;
  summary?: string;
};

export function RiskRatingCard({ rating, summary }: RiskRatingCardProps) {
  return (
    <section className="panel risk-panel" aria-label="Risk rating">
      <p className="eyebrow">Risk rating</p>
      <h2>{rating}</h2>
      <p className="risk-tone">{riskTone(rating)} attention required</p>
      {summary ? <p>{summary}</p> : null}
    </section>
  );
}
