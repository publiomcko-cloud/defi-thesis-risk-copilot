import { DisclaimerBox } from "@/components/DisclaimerBox";
import { WatchlistTable } from "@/components/WatchlistTable";

export default function WatchlistPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">In-app alerts</p>
        <h1>Watchlist</h1>
        <p>
          Create watched strategies or markets, evaluate rule thresholds
          manually, and review stored in-app alert events.
        </p>
      </section>

      <WatchlistTable />
      <DisclaimerBox text="Watchlist alerts are analytical reminders only. They do not send push or email notifications, execute trades, or recommend buying or selling." />
    </main>
  );
}
