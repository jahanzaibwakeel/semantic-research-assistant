import { BookOpen } from "lucide-react";
import type { Citation } from "@/lib/api";

export function SourceList({ sources }: { sources: Citation[] }) {
  if (!sources.length) return null;
  return (
    <div className="space-y-3">
      {sources.map((source, index) => (
        <div key={`${source.document_id}-${source.chunk_index}-${index}`} className="rounded-lg border border-stone-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <BookOpen size={16} />
            <span>[{index + 1}] {source.filename}</span>
            {source.page ? <span className="text-stone-500">page {source.page}</span> : null}
          </div>
          <div className="mt-1 text-xs text-stone-500">
            {source.retrieval_method} relevance {source.score ? source.score.toFixed(2) : "n/a"}
          </div>
          <p className="mt-2 text-sm leading-6 text-stone-700">{source.excerpt}</p>
        </div>
      ))}
    </div>
  );
}
