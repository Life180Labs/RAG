import { CacheDashboard } from '@/components/cache/cache-dashboard';
import { HealthDashboard } from '@/components/health-dashboard';

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-foreground text-xl font-semibold">Platform Overview</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Live status of API health and cache performance.
        </p>
      </div>
      <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
        <HealthDashboard />
        <CacheDashboard />
      </div>
    </div>
  );
}
