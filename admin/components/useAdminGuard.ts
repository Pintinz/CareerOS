"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getAdminToken } from "@/lib/adminAuth";

/** Redirects to /login when no admin token is present. Returns whether the check has
 * finished, so pages can avoid a content flash before the redirect fires. */
export function useAdminGuard(): { checked: boolean } {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!getAdminToken()) {
      router.replace("/login");
    } else {
      setChecked(true);
    }
  }, [router]);

  return { checked };
}
