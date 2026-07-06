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

  if (!user) return null;

  const initials = user.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user.email.slice(0, 2).toUpperCase();

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
    <div className="w-full max-w-md space-y-4">
      <div className="flex items-center gap-4">
        <div className="bg-primary/20 text-primary flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-sm font-semibold">
          {initials}
        </div>
        <div>
          <p className="text-foreground font-semibold">{user.full_name || user.email}</p>
          <p className="text-muted-foreground text-sm">{user.email}</p>
        </div>
        <Badge variant="secondary" className="ml-auto">
          {user.role}
        </Badge>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Account details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="divide-border divide-y text-sm">
            <div className="flex justify-between py-2.5">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="text-foreground font-medium">{user.email}</dd>
            </div>
            <div className="flex justify-between py-2.5">
              <dt className="text-muted-foreground">Member since</dt>
              <dd className="text-foreground font-medium">
                {new Date(user.created_at).toLocaleDateString()}
              </dd>
            </div>
          </dl>

          <form className="space-y-3 pt-2" onSubmit={handleSubmit}>
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

            <div className="space-y-1.5">
              <Label htmlFor="full_name">Full name</Label>
              <Input
                id="full_name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>

            <Button type="submit" size="sm" disabled={isSubmitting}>
              {isSubmitting ? 'Saving…' : 'Save changes'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Button variant="outline" className="w-full" onClick={() => logout()}>
        Sign out
      </Button>
    </div>
  );
}
