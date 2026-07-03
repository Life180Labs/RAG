import { AuthGuard } from '@/components/auth-guard';
import { ProfileView } from '@/components/auth/profile-view';

export default function ProfilePage() {
  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <AuthGuard>
        <ProfileView />
      </AuthGuard>
    </main>
  );
}
