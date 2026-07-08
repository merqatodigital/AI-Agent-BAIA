import { KnowledgeCategoryList } from "@/components/admin/KnowledgeManager";

export const dynamic = "force-dynamic";

export default function KnowledgePage() {
  return (
    <div className="max-w-4xl">
      <p className="eyebrow">Owner · Knowledge Base</p>
      <h1 className="mt-2 font-serif text-4xl">Resort knowledge</h1>
      <p className="mt-3 text-sm text-ink/70">
        The concierge only ever answers from verified, published knowledge.
        Edits create immutable draft versions; nothing reaches guests until you
        verify and publish it.
      </p>
      <KnowledgeCategoryList />
    </div>
  );
}
