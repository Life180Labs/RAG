import { Suspense } from 'react';

import { ResetPasswordForm } from '@/components/auth/reset-password-form';
import { Skeleton } from '@/components/ui/skeleton';

export default function ResetPasswordPage() {
  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <Suspense fallback={<Skeleton className="h-64 w-full max-w-sm" />}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
