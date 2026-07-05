import { AuthGuard } from '@/components/auth-guard';
import { OrganizationDetail } from '@/components/tenancy/organization-detail';

export default async function OrganizationDetailPage({
  params,
}: {
  params: Promise<{ organizationId: string }>;
}) {
  const { organizationId } = await params;

  return (
    <AuthGuard>
      <OrganizationDetail organizationId={organizationId} />
    </AuthGuard>
  );
}
