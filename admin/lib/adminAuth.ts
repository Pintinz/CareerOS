"use client";

const TOKEN_KEY = "careeros_admin_access_token";

// Dev-simple session storage. Revisit for httpOnly cookies + refresh-token rotation before
// this admin app is ever exposed beyond localhost (see PROJECT_STATUS.md known issues).
export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}
