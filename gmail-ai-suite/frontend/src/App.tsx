import React, { useState } from "react";
import { useEmails, Email } from "./hooks/useEmails";
import { format } from "date-fns";

// --- shadcn/ui ---
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "./components/ui/card";
import { Button } from "./components/ui/button";

// ドロップダウン選択肢
const CATEGORIES = [
  "すべて",
  "業務連絡",
  "宣伝",
  "プライベート",
  "重要",
  "分類失敗",
];
const PRIORITIES = ["すべて", "1", "2", "3", "4", "5"];
const COUNTS = [5, 10, 20, 50];

export default function App() {
  const { emails, loading } = useEmails();

  // フィルタ状態
  const [selectedCategory, setSelectedCategory] = useState("すべて");
  const [selectedPriority, setSelectedPriority] = useState("すべて");
  const [visibleCount, setVisibleCount] = useState(10);

  // フィルタ処理
  const filtered = emails.filter((e: Email) => {
    const okCat = selectedCategory === "すべて" || e.category === selectedCategory;
    const okPri =
      selectedPriority === "すべて" || e.priority_score === Number(selectedPriority);
    return okCat && okPri;
  });

  const displayed = filtered.slice(0, visibleCount);

  return (
    <div className="min-h-screen bg-gray-50 py-6">
      <Card className="mx-auto max-w-6xl shadow">
        <CardHeader>
          <CardTitle className="text-2xl">📧 メール一覧（フィルタ付き）</CardTitle>
        </CardHeader>

        <CardContent className="space-y-6 px-6 pb-8">
          {/* フィルタ UI */}
          <div className="flex flex-wrap gap-6">
            {/* カテゴリ */}
            <label className="flex items-center gap-2 text-sm">
              カテゴリ:
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2"
              >
                {CATEGORIES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>

            {/* 優先度 */}
            <label className="flex items-center gap-2 text-sm">
              優先度:
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2"
              >
                {PRIORITIES.map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </label>

            {/* 表示件数 */}
            <label className="flex items-center gap-2 text-sm">
              表示件数:
              <select
                value={visibleCount}
                onChange={(e) => setVisibleCount(Number(e.target.value))}
                className="rounded-md border border-gray-300 px-3 py-2"
              >
                {COUNTS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* 結果表示 */}
          {loading ? (
            <p>読み込み中...</p>
          ) : displayed.length === 0 ? (
            <p>該当するメールがありません。</p>
          ) : (
            <>
              <p className="text-sm text-gray-600">
                全 {emails.length} 件中 {displayed.length} 件を表示中
              </p>

              <div className="overflow-auto rounded-lg border">
                <table className="min-w-full table-fixed text-sm">
                  <thead className="bg-gray-100 text-left text-xs font-medium">
                    <tr>
                      <th className="border border-gray-500 px-4 py-2 bg-gray-200">件名</th>
                      <th className="border border-gray-500 px-4 py-2 bg-gray-200">送信者</th>
                      <th className="border border-gray-500 px-4 py-2 bg-gray-200">日付</th>
                      <th className="border border-gray-500 px-4 py-2 bg-gray-200">カテゴリ</th>
                      <th className="border border-gray-500 px-4 py-2 bg-gray-200">優先度</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayed.map((email, idx) => (
                      <tr
                        key={email.id}
                        className={
                          idx % 2
                            ? "bg-gray-200 hover:bg-gray-300"
                            : "bg-white hover:bg-gray-100"
                        }
                      >
                        <td className="border border-gray-500 px-4 py-2">{email.subject}</td>
                        <td className="border border-gray-500 px-4 py-2">{email.from}</td>
                        <td className="border border-gray-500 px-4 py-2">
                          {format(new Date(email.date), "yyyy/MM/dd HH:mm")}
                        </td>
                        <td className="border border-gray-500 px-4 py-2">{email.category}</td>
                        <td className="border border-gray-500 px-4 py-2">{email.priority_score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* “さらに表示” ボタン */}
              {filtered.length > visibleCount && (
                <div className="flex justify-center pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setVisibleCount((c) => c + 50)}
                  >
                    さらに表示
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
