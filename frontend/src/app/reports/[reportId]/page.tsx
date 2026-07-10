import { ReportViewer } from "./report-viewer";

type ReportPageProps = {
  params: Promise<{
    reportId: string;
  }>;
};

export default async function ReportPage({ params }: ReportPageProps) {
  const { reportId } = await params;
  return <ReportViewer reportId={reportId} />;
}
