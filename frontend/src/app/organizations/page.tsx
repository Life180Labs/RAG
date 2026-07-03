import { AuthGuard } from '@/components/auth-guard';
import { OrganizationList } from '@/components/tenancy/organization-list';

export default function OrganizationsPage() {
  return (
    <main className="flex flex-1 justify-center p-8">
      <AuthGuard>
        <OrganizationList />
      </AuthGuard>
    </main>
  );
}
