"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Category {
  id: number;
  name: string;
}

interface Rule {
  id: number;
  keyword: string;
  category: string | null;
  subcategory: string | null;
  status: string;
  created_at: string;
  priority: number;
}

export default function RulesPage() {
  const [csrf, setCsrf] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      // Load CSRF token
      let token: string | null = null;
      try {
        token = localStorage.getItem("csrfToken");
      } catch (e) {
        /* ignore */
      }
      if (!token) {
        const r = await fetch(`${API}/api/csrf`, { credentials: "include" });
        if (r.ok) {
          const d = await r.json();
          token = d.csrf;
          try {
            localStorage.setItem("csrfToken", token);
          } catch (e) {
            /* ignore */
          }
        }
      }
      setCsrf(token);
      refreshCategories();
      refreshRules();
    }
    init();
  }, []);

  async function refreshCategories() {
    const r = await fetch(`${API}/api/categories`, { credentials: "include" });
    if (r.ok) {
      const data = await r.json();
      setCategories(data);
    }
  }

  async function refreshRules() {
    const r = await fetch(`${API}/api/rules`, { credentials: "include" });
    if (r.ok) {
      const data = await r.json();
      setRules(data);
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!keyword.trim()) {
      setMessage("Keyword is required");
      return;
    }
    if (!csrf) return;
    setLoading(true);
    setMessage(null);
    const payload: any = { keyword: keyword.trim() };
    if (category) payload.category = category;
    if (subcategory) payload.subcategory = subcategory.trim();
    try {
      const r = await fetch(`${API}/api/rules`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-csrf-token": csrf,
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (r.ok) {
        setKeyword("");
        setCategory("");
        setSubcategory("");
        setMessage("Rule added");
        refreshRules();
      } else {
        setMessage("Failed to add rule");
      }
    } catch (err) {
      setMessage("Error adding rule");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!csrf) return;
    const ok = confirm("Delete this rule?");
    if (!ok) return;
    const r = await fetch(`${API}/api/rules/${id}`, {
      method: "DELETE",
      headers: { "x-csrf-token": csrf },
      credentials: "include",
    });
    if (r.ok) {
      refreshRules();
    }
  }

  async function handleReprocess() {
    if (!csrf) return;
    setLoading(true);
    setMessage(null);
    const r = await fetch(`${API}/api/reprocess`, {
      method: "POST",
      headers: { "x-csrf-token": csrf },
      credentials: "include",
    });
    if (r.ok) {
      setMessage("Reprocessing complete");
    } else {
      setMessage("Failed to reprocess");
    }
    setLoading(false);
  }

  function statusBadge(status: string) {
    const base =
      "inline-block rounded-full px-2 py-0.5 text-xs font-medium";
    if (status === "active") {
      return <span className={`${base} bg-green-100 text-green-800`}>Active</span>;
    }
    return <span className={`${base} bg-gray-100 text-gray-800`}>{status}</span>;
  }

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-6">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Categorization Rules</h1>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={handleReprocess}
            disabled={loading || !csrf}
            className="rounded bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Re-categorize All
          </button>
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </div>

      {/* Add Rule Form */}
      <div className="rounded-lg border bg-white shadow-sm">
        <div className="border-b px-6 py-4 text-lg font-medium">
          Add New Rule
        </div>
        <form onSubmit={handleAdd} className="p-6 space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Keyword
              </label>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:outline-none"
                placeholder="e.g., STRIPE"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded border border-gray-300 p-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="">Select Category</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Subcategory (Optional)
              </label>
              <input
                type="text"
                value={subcategory}
                onChange={(e) => setSubcategory(e.target.value)}
                className="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:outline-none"
                placeholder="e.g., Online Payments"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || !csrf}
            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Adding…" : "Add Rule"}
          </button>
          {message && <p className="text-sm text-gray-600">{message}</p>}
          {/* How it works panel */}
          <div className="rounded-md bg-blue-50 p-4 text-sm text-blue-800">
            <p className="font-medium">How it works:</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>Rules are applied in order when processing transactions</li>
              <li>First matching rule wins (case-insensitive keyword search)</li>
              <li>Manual categories always override automatic rules</li>
              <li>
                Use <span className="font-semibold">Re-categorize All</span> to apply
                new rules to existing transactions
              </li>
            </ul>
          </div>
        </form>
      </div>

      {/* Active Rules Table */}
      <div className="rounded-lg border bg-white shadow-sm">
        <div className="border-b px-6 py-4 text-lg font-medium">
          Active Rules
        </div>
        <div className="p-6 overflow-x-auto">
          {rules.length === 0 ? (
            <div className="text-sm text-gray-600">No rules defined yet.</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th className="py-2">Keyword</th>
                  <th className="py-2">Category</th>
                  <th className="py-2">Subcategory</th>
                  <th className="py-2">Status</th>
                  <th className="py-2">Created</th>
                  <th className="py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id} className="border-t">
                    <td className="py-2">{r.keyword}</td>
                    <td className="py-2">{r.category || ""}</td>
                    <td className="py-2">{r.subcategory || ""}</td>
                    <td className="py-2">{statusBadge(r.status)}</td>
                    <td className="py-2">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2">
                      <button
                        onClick={() => handleDelete(r.id)}
                        className="text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}