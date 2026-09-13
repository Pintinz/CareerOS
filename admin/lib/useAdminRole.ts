"use client";

import { useEffect, useState } from "react";

import { api } from "./apiClient";
import { getAdminToken } from "./adminAuth";

export type AdminRole = "SUPER_ADMIN" | "ADMIN" | "EDITOR" | "REVIEWER";

interface AdminMe {
  id: string;
  email: string;
  role: AdminRole;
}

/** Fetches the signed-in admin's role once, for nav-visibility purposes only — the backend
 * remains the authoritative RBAC check on every route (spec §2); this never gates an action by
 * itself. */
export function useAdminRole(): { role: AdminRole | null; loading: boolean } {
  const [role, setRole] = useState<AdminRole | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAdminToken()) {
      setLoading(false);
      return;
    }
    api
      .get<AdminMe>("/admin/auth/me")
      .then((me) => setRole(me.role))
      .catch(() => setRole(null))
      .finally(() => setLoading(false));
  }, []);

  return { role, loading };
}
