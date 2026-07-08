import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";
import { ResortEditor } from "@/components/admin/ResortEditor";

export const dynamic = "force-dynamic";

export default async function ResortEditorPage() {
  const store = getDataStore();
  const profile = await store.getResortProfile(DEFAULT_RESORT_ID);

  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Content</p>
      <h1 className="mt-2 font-serif text-4xl">Resort Editor</h1>
      <p className="mt-3 text-sm text-ink/70">
        Every word, image and policy on your website is editable here. Nothing
        is hardcoded.
      </p>
      <div className="mt-8">
        <ResortEditor profile={profile} />
      </div>
    </div>
  );
}
