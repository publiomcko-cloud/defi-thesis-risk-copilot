import { JobsWorkspace } from "@/components/JobsWorkspace";

export default function JobsPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Account</p>
        <h1>Jobs</h1>
        <p>Review the progress and results of your private queued work.</p>
      </section>
      <JobsWorkspace />
    </main>
  );
}
