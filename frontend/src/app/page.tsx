import { HealthDashboard } from '@/components/health-dashboard';
import { TopNav } from '@/components/top-nav';

export default function HomePage() {
  return (
    <>
      <TopNav />
      <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Enterprise RAG Studio</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Every stage of the RAG pipeline, observable end to end.
          </p>
        </div>
        <HealthDashboard />
      </main>
    </>
  );
}
