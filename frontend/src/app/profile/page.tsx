import { AuthGuard } from '@/components/auth-guard';
import { ProfileView } from '@/components/auth/profile-view';

export default function ProfilePage() {
  return (
    <AuthGuard>
      <ProfileView />
    </AuthGuard>
  );
}
