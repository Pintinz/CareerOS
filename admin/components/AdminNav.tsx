"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { BrandLockup } from "@/components/BrandMark";
import {
  IconBell,
  IconBriefcase,
  IconBuilding,
  IconDashboard,
  IconGraduation,
  IconImage,
  IconInsights,
  IconLink,
  IconLogout,
  IconMic,
  IconPulse,
  IconQuiz,
  IconSearch,
  IconSettings,
  IconShield,
  IconUsers,
} from "@/components/icons";
import { clearAdminToken } from "@/lib/adminAuth";
import { useAdminRole } from "@/lib/useAdminRole";

type NavLink = { href: string; label: string; icon: ReactNode; roles?: string[] };
type NavGroup = { title?: string; links: NavLink[] };

// Order follows admin-design.md: Dashboard · Jobs · Scholarships · Companies · Intelligence ·
// Question Banks · Media · Sources · Discovery · Users · Notifications · Operations · Audit Logs ·
// Settings.
const GROUPS: NavGroup[] = [
  { links: [{ href: "/", label: "Dashboard", icon: <IconDashboard /> }] },
  {
    title: "Content",
    links: [
      { href: "/jobs", label: "Jobs", icon: <IconBriefcase /> },
      { href: "/scholarships", label: "Scholarships", icon: <IconGraduation /> },
      { href: "/companies", label: "Companies", icon: <IconBuilding /> },
      { href: "/intelligence", label: "Intelligence", icon: <IconInsights /> },
    ],
  },
  {
    title: "Question Banks",
    links: [
      { href: "/questions/aptitude", label: "Aptitude", icon: <IconQuiz /> },
      { href: "/questions/interview", label: "Interview", icon: <IconMic /> },
    ],
  },
  {
    title: "Pipeline",
    links: [
      { href: "/media", label: "Media", icon: <IconImage /> },
      { href: "/sources", label: "Sources", icon: <IconLink /> },
      { href: "/discovery", label: "Discovery", icon: <IconSearch /> },
    ],
  },
  {
    title: "People & Ops",
    links: [
      { href: "/users", label: "Users", icon: <IconUsers /> },
      { href: "/notifications", label: "Notifications", icon: <IconBell /> },
      { href: "/operations", label: "Operations", icon: <IconPulse /> },
    ],
  },
  {
    // Spec §34/§35 — audit logs and system settings are more sensitive than ordinary content and are
    // hidden from EDITOR/REVIEWER navigation. The backend enforces this independently regardless of
    // what this array shows (spec §2: "Backend authorization remains authoritative").
    title: "System",
    links: [
      { href: "/audit", label: "Audit Logs", icon: <IconShield />, roles: ["SUPER_ADMIN", "ADMIN"] },
      { href: "/settings", label: "Settings", icon: <IconSettings />, roles: ["SUPER_ADMIN"] },
    ],
  },
];

export function AdminNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { role } = useAdminRole();

  if (pathname === "/login") return null;

  return (
    <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col bg-navy text-white">
      <div className="px-5 pb-4 pt-6">
        <Link href="/" aria-label="CareerOS Admin home">
          <BrandLockup onDark suffix="Admin" />
        </Link>
      </div>
      <nav aria-label="Admin" className="flex-1 overflow-y-auto px-3 pb-4">
        {GROUPS.map((group, index) => {
          const links = group.links.filter((link) => !link.roles || !role || link.roles.includes(role));
          if (links.length === 0) return null;
          return (
            <div key={group.title ?? index} className="mt-4 first:mt-0">
              {group.title && (
                <p className="mb-1.5 px-3 text-[0.68rem] font-semibold uppercase tracking-wider text-white/40">{group.title}</p>
              )}
              {links.map((link) => {
                const active = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    aria-current={active ? "page" : undefined}
                    className={`mb-0.5 flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors ${
                      active ? "bg-brand text-white shadow-[0_6px_16px_rgba(22,119,255,0.35)]" : "text-white/70 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <span className={active ? "text-white" : "text-white/60"}>{link.icon}</span>
                    {link.label}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>
      <div className="border-t border-white/10 px-3 py-4">
        {role && <p className="mb-2 px-3 text-xs text-white/40">Signed in as {role.replace("_", " ").toLowerCase()}</p>}
        <button
          onClick={() => {
            clearAdminToken();
            router.push("/login");
          }}
          className="flex h-10 w-full items-center gap-3 rounded-lg px-3 text-left text-sm font-medium text-white/70 transition-colors hover:bg-white/10 hover:text-white"
        >
          <IconLogout />
          Log out
        </button>
      </div>
    </aside>
  );
}
