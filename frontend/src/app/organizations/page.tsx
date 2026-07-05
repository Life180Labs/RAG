import { AuthGuard } from '@/components/auth-guard';
import { OrganizationList } from '@/components/tenancy/organization-list';

export default function OrganizationsPage() {
  return (
    <AuthGuard>
      <OrganizationList />
    </AuthGuard>
  );
}
