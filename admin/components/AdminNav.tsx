"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearAdminToken } from "@/lib/adminAuth";
import { useAdminRole } from "@/lib/useAdminRole";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/scholarships", label: "Scholarships" },
  { href: "/intelligence", label: "Intelligence" },
  { href: "/companies", label: "Companies" },
  { href: "/questions/aptitude", label: "Aptitude Questions" },
  { href: "/questions/interview", label: "Interview Questions" },
  { href: "/media", label: "Media" },
  { href: "/sources", label: "Sources" },
  { href: "/discovery", label: "Discovery" },
  { href: "/users", label: "Users" },
  { href: "/notifications", label: "Notifications" },
  { href: "/operations", label: "Operations" },
];

// Spec §34/§35 — audit logs and system settings are more sensitive than ordinary content and are
// hidden from EDITOR/REVIEWER navigation. The backend enforces this independently regardless of
// what this array shows (spec §2: "Backend authorization remains authoritative").
const RESTRICTED_LINKS = [
  { href: "/audit", label: "Audit Logs", roles: ["SUPER_ADMIN", "ADMIN"] },
  { href: "/settings", label: "Settings", roles: ["SUPER_ADMIN"] },
];

export function AdminNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { role } = useAdminRole();

  if (pathname === "/login") return null;

  const visibleRestricted = RESTRICTED_LINKS.filter((link) => !role || link.roles.includes(role));

  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col bg-navy text-white">
      <div className="px-5 py-5">
        <p className="text-sm font-semibold tracking-wide">CareerOS</p>
        <p className="text-xs text-white/60">Admin</p>
      </div>
      <nav className="flex-1 overflow-y-auto px-3">
        {LINKS.map((link) => {
          const active = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`mb-1 block rounded-lg px-3 py-2 text-sm transition-colors ${
                active ? "bg-brand text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
        {visibleRestricted.length > 0 && <div className="my-2 border-t border-white/10" />}
        {visibleRestricted.map((link) => {
          const active = pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`mb-1 block rounded-lg px-3 py-2 text-sm transition-colors ${
                active ? "bg-brand text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-3 pb-5">
        <button
          onClick={() => {
            clearAdminToken();
            router.push("/login");
          }}
          className="w-full rounded-lg px-3 py-2 text-left text-sm text-white/70 hover:bg-white/10 hover:text-danger"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
