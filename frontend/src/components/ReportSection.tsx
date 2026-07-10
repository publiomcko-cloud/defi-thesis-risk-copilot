import type { ReportSection as ReportSectionType } from "@/lib/types";

type ReportSectionProps = {
  section: ReportSectionType;
};

export function ReportSection({ section }: ReportSectionProps) {
  return (
    <section className="panel">
      <h2>{section.title}</h2>
      <p>{section.content}</p>
    </section>
  );
}
