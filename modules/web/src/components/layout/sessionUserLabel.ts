import type { BffUser } from "@/api/auth";

/** Prefer display name, then username, then email for the shell chip. */
export function sessionUserLabel(user: BffUser): string {
  const displayName = user.display_name?.trim();
  if (displayName) {
    return displayName;
  }
  const username = user.username?.trim();
  if (username) {
    return username;
  }
  return user.email;
}
