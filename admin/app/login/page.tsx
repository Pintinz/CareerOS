"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BrandLockup, BrandMark } from "@/components/BrandMark";
import { setAdminToken } from "@/lib/adminAuth";
import { ApiError, api } from "@/lib/apiClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await api.post<{ access_token: string }>("/admin/auth/login", {
        email,
        password,
      });
      setAdminToken(response.access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen w-full lg:grid-cols-2">
      <section className="relative hidden overflow-hidden bg-navy p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <BrandLockup onDark suffix="Admin" />
        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-bold leading-tight">Publish opportunities people can trust.</h2>
          <p className="mt-3 text-white/70">Manage jobs, scholarships, company intelligence and question banks for CareerOS.</p>
        </div>
        <p className="text-sm text-white/40">Opportunities Today. A Brighter You Tomorrow.</p>
        <div className="pointer-events-none absolute -bottom-24 -right-24 opacity-10" aria-hidden>
          <BrandMark size={420} onDark decorative />
        </div>
      </section>

      <section className="flex items-center justify-center px-6 py-12">
        <form onSubmit={handleSubmit} className="w-full max-w-sm" aria-labelledby="signin-title">
          <div className="mb-8 lg:hidden">
            <BrandLockup suffix="Admin" />
          </div>
          <h1 id="signin-title" className="text-2xl font-bold text-navy">
            Sign in
          </h1>
          <p className="mt-1 text-sm text-muted">Administrator access only.</p>

          <div className="mt-8 space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-line px-3 py-2.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-line px-3 py-2.5 text-sm"
              />
            </div>
          </div>

          {error && (
            <p role="alert" className="mt-4 rounded-lg bg-danger/5 px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <button type="submit" disabled={loading} className="btn-primary mt-6 w-full py-2.5">
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
