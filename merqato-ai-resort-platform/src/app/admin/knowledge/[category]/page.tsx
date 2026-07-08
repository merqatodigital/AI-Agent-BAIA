import Link from "next/link";
import { KnowledgeCategoryManager } from "@/components/admin/KnowledgeManager";

export const dynamic = "force-dynamic";

const LABELS: Record<string, string> = {
  identity: "Identity",
  rooms: "Rooms",
  rates: "Rates",
  amenities: "Amenities",
  policies: "Policies",
  wifi_power: "Wi-Fi & Power",
  food_breakfast: "Food & Breakfast",
  transport: "Transport",
  emergency_contacts: "Emergency Contacts",
  faq: "FAQ",
};

export default async function KnowledgeCategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = await params;
  const label = LABELS[category] ?? category;

  return (
    <div className="max-w-4xl">
      <p className="eyebrow">
        <Link href="/admin/knowledge" className="no-underline hover:text-accent">
          Knowledge Base
        </Link>{" "}
        · {label}
      </p>
      <h1 className="mt-2 font-serif text-4xl">{label}</h1>
      <div className="mt-8">
        <KnowledgeCategoryManager category={category} />
      </div>
    </div>
  );
}
