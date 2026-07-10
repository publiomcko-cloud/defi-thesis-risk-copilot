import type { RiskRating } from "./types";

export function riskTone(rating: RiskRating): string {
  switch (rating) {
    case "Conservative":
      return "Low";
    case "Moderate":
      return "Medium";
    case "Aggressive":
      return "High";
    case "Very Risky":
      return "Extreme";
  }
}

export function formatProtocolName(protocol: string): string {
  return protocol.charAt(0).toUpperCase() + protocol.slice(1);
}
