import { AuthGuard } from '@/components/auth-guard';
import { ProviderCredentialsPanel } from '@/components/settings/provider-credentials-panel';

export default async function OrganizationSettingsPage({
  params,
}: {
  params: Promise<{ organizationId: string }>;
}) {
  const { organizationId } = await params;

  return (
    <AuthGuard>
      <ProviderCredentialsPanel organizationId={organizationId} />
    </AuthGuard>
  );
}
