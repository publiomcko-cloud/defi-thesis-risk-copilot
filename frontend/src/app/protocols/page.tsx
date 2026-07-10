import { fetchProtocols } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ProtocolsPage() {
  let protocols = [
    {
      id: "pendle",
      name: "Pendle",
      category: "fixed-yield",
      supported_in_mvp: true,
      description: "Fixed-yield and principal token strategies."
    },
    {
      id: "morpho",
      name: "Morpho",
      category: "lending",
      supported_in_mvp: true,
      description: "Isolated lending markets and vault-based lending."
    },
    {
      id: "aave",
      name: "Aave",
      category: "lending",
      supported_in_mvp: true,
      description: "Collateralized lending, borrowing, and health factor risk."
    }
  ];

  try {
    const response = await fetchProtocols();
    protocols = response.protocols;
  } catch {
    // The static fallback keeps the page useful when the backend is offline.
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">MVP protocol scope</p>
        <h1>Supported Protocols</h1>
        <p>
          The backend uses this MVP protocol scope for curated RAG retrieval,
          market data adapter selection, and deterministic risk scoring.
        </p>
      </section>

      <section className="content-grid">
        {protocols.map((protocol) => (
          <article className="panel" key={protocol.id}>
            <p className="eyebrow">{protocol.category}</p>
            <h2>{protocol.name}</h2>
            <p>{protocol.description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
