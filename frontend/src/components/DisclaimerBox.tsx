type DisclaimerBoxProps = {
  text?: string;
};

const defaultDisclaimer =
  "Research and education only. This MVP does not connect wallets, sign transactions, execute trades, custody funds, or provide personalized financial advice.";

export function DisclaimerBox({ text = defaultDisclaimer }: DisclaimerBoxProps) {
  return (
    <section className="notice" aria-label="Safety disclaimer">
      <h2>Safety Boundary</h2>
      <p>{text}</p>
    </section>
  );
}
