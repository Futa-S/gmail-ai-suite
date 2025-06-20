import { useEffect, useState } from "react";

/* ---- App.tsx が期待する型 ---- */
export interface Email {
  id: string;
  from: string;          // ← alias of sender
  to?: string;
  cc?: string;
  subject: string;
  date: string;
  snippet: string;
  category: string | null;   // ← alias of category_pred
  priority_score?: number;
}

/* ------------- フック ------------- */
export function useEmails(days = 7, limit = 10) {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const url = `http://localhost:8000/emails/?days=${days}&max_results=${limit}`;

    fetch(url, { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        /* ---- バックエンド → フロント用キーへの変換 ---- */
        const normalized: Email[] = data.map((e: any) => ({
          id: e.id,
          from: e.sender,                 // sender → from
          subject: e.subject,
          date: e.date,
          snippet: e.snippet,
          category: e.category_pred,      // category_pred → category
          priority_score: e.priority_score ?? null,
          to: e.to ?? "",
          cc: e.cc ?? "",
        }));
        setEmails(normalized);
      })
      .catch((err) => {
        console.error("メール取得エラー:", err);
        setEmails([]);
      })
      .finally(() => setLoading(false));
  }, [days, limit]);

  return { emails, loading };
}
