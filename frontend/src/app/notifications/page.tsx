import { NotificationCenter } from "@/components/NotificationCenter";

export default function NotificationsPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Account</p>
        <h1>Notifications</h1>
        <p>Review private in-app updates and control how non-mandatory notifications surface.</p>
      </section>
      <NotificationCenter />
    </main>
  );
}
