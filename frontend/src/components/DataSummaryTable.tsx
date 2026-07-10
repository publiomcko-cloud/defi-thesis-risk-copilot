type DataSummaryTableProps = {
  assumptions?: string[];
  missingData?: string[];
};

export function DataSummaryTable({
  assumptions = [],
  missingData = []
}: DataSummaryTableProps) {
  return (
    <section className="panel">
      <h2>Data Summary</h2>
      <div className="data-grid">
        <div>
          <h3>Assumptions</h3>
          <ul>
            {assumptions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>Missing Data</h3>
          <ul>
            {missingData.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
