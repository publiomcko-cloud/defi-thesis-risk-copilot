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
              <span>{source.source_type}{source.protocol ? ` · ${source.protocol}` : ""}</span>
              {source.url ? (
                <a className="text-link" href={source.url} rel="noreferrer" target="_blank">
                  Open source
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
