'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/providers/auth-provider';
import { ApiRequestError } from '@/services/api-client';
import { updateMe } from '@/services/auth-service';

export function ProfileView() {
  const { user, refreshUser, logout } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!user) {
    // AuthGuard only renders this component once authenticated, but the
    // type is nullable — this satisfies the empty state requirement.
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSubmitting(true);
    try {
      await updateMe({ full_name: fullName });
      await refreshUser();
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to update profile.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Profile</CardTitle>
        <Badge variant="secondary">{user.role}</Badge>
      </CardHeader>
      <CardContent className="space-y-6">
        <dl className="text-sm">
          <div className="flex justify-between py-1">
            <dt className="text-muted-foreground">Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div className="flex justify-between py-1">
            <dt className="text-muted-foreground">Member since</dt>
            <dd>{new Date(user.created_at).toLocaleDateString()}</dd>
          </div>
        </dl>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Update failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert data-testid="profile-update-success">
              <AlertTitle>Profile updated</AlertTitle>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="full_name">Full name</Label>
            <Input
              id="full_name"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Save changes'}
          </Button>
        </form>

        <Button variant="outline" className="w-full" onClick={() => logout()}>
          Sign out
        </Button>
      </CardContent>
    </Card>
  );
}
