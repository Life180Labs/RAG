// Mirrors backend/app/schemas/auth.py::_validate_password_strength so the
// user sees the same rule client-side instead of only after a round trip.
export function validatePassword(password: string): string | null {
  if (password.length < 12) return 'Password must be at least 12 characters long.';
  if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter.';
  if (!/[a-z]/.test(password)) return 'Password must contain at least one lowercase letter.';
  if (!/\d/.test(password)) return 'Password must contain at least one digit.';
  if (!/[^A-Za-z0-9]/.test(password))
    return 'Password must contain at least one special character.';
  return null;
}
