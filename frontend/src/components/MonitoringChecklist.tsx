type MonitoringChecklistProps = {
  items?: string[];
};

const defaultItems = [
  "Borrow APY and utilization",
  "Secondary-market liquidity and slippage",
  "Oracle status and data freshness",
  "Collateral price movement",
  "PT maturity and exit timing",
  "Protocol governance or parameter changes"
];

export function MonitoringChecklist({
  items = defaultItems
}: MonitoringChecklistProps) {
  return (
    <section className="panel">
      <h2>Monitoring Checklist</h2>
      <ul className="check-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
