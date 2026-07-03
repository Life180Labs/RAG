import { AuthGuard } from '@/components/auth-guard';
import { OrganizationDetail } from '@/components/tenancy/organization-detail';

export default async function OrganizationDetailPage({
  params,
}: {
  params: Promise<{ organizationId: string }>;
}) {
  const { organizationId } = await params;

  return (
    <main className="flex flex-1 justify-center p-8">
      <AuthGuard>
        <OrganizationDetail organizationId={organizationId} />
      </AuthGuard>
    </main>
  );
}
