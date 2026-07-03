'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useInviteMember } from '@/hooks/use-tenancy';
import { ApiRequestError } from '@/services/api-client';
import type { MemberRole } from '@/types/tenancy';

const ROLES: MemberRole[] = ['admin', 'developer', 'viewer'];

export function InviteMemberForm({ organizationId }: { organizationId: string }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<MemberRole>('developer');
  const [error, setError] = useState<string | null>(null);
  const [devInviteLink, setDevInviteLink] = useState<string | null>(null);
  const inviteMember = useInviteMember(organizationId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setDevInviteLink(null);
    try {
      const response = await inviteMember.mutateAsync({ email, role });
      setEmail('');
      if (response.data.invite_token) {
        // Dev-only convenience — no email service exists yet.
        setDevInviteLink(response.data.invite_token);
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to send invitation.');
    }
  }

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Couldn&apos;t invite member</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {devInviteLink && (
        <Alert data-testid="invite-dev-token">
          <AlertTitle>Invitation created (dev mode)</AlertTitle>
          <AlertDescription className="break-all">
            No email service is configured yet — share this token manually: {devInviteLink}
          </AlertDescription>
        </Alert>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1 space-y-1">
          <Label htmlFor="invite-email">Email</Label>
          <Input
            id="invite-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="invite-role">Role</Label>
          <select
            id="invite-role"
            className="border-input bg-background h-8 rounded-lg border px-2.5 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value as MemberRole)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" disabled={inviteMember.isPending}>
          {inviteMember.isPending ? 'Sending…' : 'Invite'}
        </Button>
      </div>
    </form>
  );
}
