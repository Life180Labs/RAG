import { CacheDashboard } from '@/components/cache/cache-dashboard';
import { HealthDashboard } from '@/components/health-dashboard';

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Platform Overview</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Live status of API health and cache performance.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 max-w-2xl">
        <HealthDashboard />
        <CacheDashboard />
      </div>
    </div>
  );
}
