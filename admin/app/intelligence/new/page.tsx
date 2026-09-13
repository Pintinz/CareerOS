"use client";

import { useRouter } from "next/navigation";

import { IntelligenceForm } from "@/components/IntelligenceForm";
import { useAdminGuard } from "@/components/useAdminGuard";

export default function NewIntelligencePage() {
  const { checked } = useAdminGuard();
  const router = useRouter();

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="mb-6 text-2xl font-bold text-navy">New intelligence post</h1>
      <IntelligenceForm onSaved={(p) => router.push(`/intelligence/${p.id}`)} />
    </main>
  );
}
