'use client';

import Link from 'next/link';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { forgotPassword } from '@/services/auth-service';
import { ApiRequestError } from '@/services/api-client';

export function ForgotPasswordForm() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [devResetToken, setDevResetToken] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await forgotPassword(email);
      setMessage(response.data.message);
      // Only present when the backend runs with DEBUG=true (no email
      // service exists yet); lets local/dev testing complete the flow.
      setDevResetToken(response.data.reset_token ?? null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Something went wrong.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Reset your password</CardTitle>
      </CardHeader>
      <CardContent>
        {message ? (
          <Alert data-testid="forgot-password-success">
            <AlertTitle>Check your email</AlertTitle>
            <AlertDescription>
              {message}
              {devResetToken && (
                <div className="mt-2">
                  <Link
                    href={`/reset-password?token=${encodeURIComponent(devResetToken)}`}
                    className="underline"
                  >
                    Dev-only: continue to reset password
                  </Link>
                </div>
              )}
            </AlertDescription>
          </Alert>
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <Alert variant="destructive">
                <AlertTitle>Request failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Sending…' : 'Send reset link'}
            </Button>
          </form>
        )}

        <p className="text-muted-foreground mt-4 text-center text-sm">
          <Link href="/login" className="hover:underline">
            Back to sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
