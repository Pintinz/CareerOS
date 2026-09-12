"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearAdminToken } from "@/lib/adminAuth";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/companies", label: "Companies" },
  { href: "/jobs", label: "Jobs" },
  { href: "/scholarships", label: "Scholarships" },
];

export function AdminNav() {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname === "/login") return null;

  return (
    <nav className="border-b border-black/5 bg-card">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-6">
          <span className="text-sm font-semibold text-navy">CareerOS Admin</span>
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm ${
                pathname === link.href ? "font-medium text-brand" : "text-muted hover:text-ink"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
        <button
          onClick={() => {
            clearAdminToken();
            router.push("/login");
          }}
          className="text-sm text-muted hover:text-danger"
        >
          Log out
        </button>
      </div>
    </nav>
  );
}
