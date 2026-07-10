import type { SourceReference } from "@/lib/types";

type SourcesPanelProps = {
  sources: SourceReference[];
};

export function SourcesPanel({ sources }: SourcesPanelProps) {
  return (
    <section className="panel">
      <h2>Sources</h2>
      {sources.length === 0 ? (
        <p>No sources returned yet.</p>
      ) : (
        <ul className="source-list">
          {sources.map((source) => (
            <li key={`${source.title}-${source.url ?? source.source_type}`}>
              <strong>{source.title}</strong>
              <span>{source.source_type}</span>
              {source.url ? <code>{source.url}</code> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
