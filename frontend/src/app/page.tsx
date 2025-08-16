"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Statement {
  id: number;
  filename: string;
  created_at: string;
  status: string;
  transactions_count: number;
  error?: string | null;
}

export default function UploadPage() {
  const router = useRouter();
  const [csrf, setCsrf] = useState<string | null>(null);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Fetch CSRF token and statements on mount
  useEffect(() => {
    async function init() {
      try {
        // fetch CSRF token from localStorage or API
        let token = null;
        try {
          token = localStorage.getItem("csrfToken");
        } catch (e) {
          /* ignore */
        }
        if (!token) {
          const r = await fetch(`${API}/api/csrf`, {
            credentials: "include",
          });
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
      } catch (err) {
        /* ignore */
      }
    }
    init();
    refreshStatements();
  }, []);

  async function refreshStatements() {
    const r = await fetch(`${API}/api/statements`, {
      credentials: "include",
    });
    if (r.ok) {
      const data = await r.json();
      setStatements(data);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !csrf) return;
    setUploading(true);
    setMessage(null);
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${API}/api/statements`, {
      method: "POST",
      body: fd,
      credentials: "include",
      headers: {
        "x-csrf-token": csrf,
      },
    });
    if (r.ok) {
      setMessage("Your statement is being processed…");
      setFile(null);
      // refresh list after a short delay
      setTimeout(() => refreshStatements(), 1000);
    } else {
      setMessage("Upload failed");
    }
    setUploading(false);
  }

  function statusBadge(status: string) {
    const base =
      "inline-block rounded-full px-2 py-0.5 text-xs font-medium";
    switch (status) {
      case "processed":
        return <span className={`${base} bg-green-100 text-green-800`}>Processed</span>;
      case "processing":
      case "uploaded":
        return <span className={`${base} bg-yellow-100 text-yellow-800`}>Pending</span>;
      case "failed":
        return <span className={`${base} bg-red-100 text-red-800`}>Failed</span>;
      default:
        return <span className={`${base} bg-gray-100 text-gray-800`}>{status}</span>;
    }
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Upload Bank Statements</h1>
        <div className="space-x-4 text-sm">
          <Link href="/rules" className="text-blue-600 hover:underline">
            Categorization Rules
          </Link>
        </div>
      </div>
      {/* Upload card */}
      <div className="rounded-lg border bg-white shadow-sm">
        <div className="border-b px-6 py-4 text-lg font-medium">
          Upload PDF Statement
        </div>
        <form onSubmit={handleUpload} className="p-6 space-y-4">
          <div className="flex flex-col items-center justify-center rounded-md border-2 border-dashed border-gray-300 p-6 text-center">
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => {
                const f = e.target.files?.[0] || null;
                setFile(f);
              }}
              className="hidden"
              id="file-input"
            />
            <label htmlFor="file-input" className="cursor-pointer">
              <span className="block text-sm font-medium text-gray-600">
                {file ? file.name : "Select PDF bank statement"}
              </span>
              <span className="mt-2 block text-xs text-gray-400">
                Only PDF files are accepted
              </span>
            </label>
          </div>
          <button
            type="submit"
            disabled={!file || !csrf || uploading}
            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? "Processing…" : "Process Statement"}
          </button>
          {message && <p className="text-sm text-gray-600">{message}</p>}
          {/* Instructions */}
          <div className="rounded-md bg-blue-50 p-4 text-sm text-blue-800">
            <ul className="list-disc space-y-1 pl-5">
              <li>Upload your bank statement in PDF format</li>
              <li>The system will automatically extract transaction data</li>
              <li>Transactions will be categorized using existing rules</li>
              <li>You can review and edit categorizations afterwards</li>
            </ul>
          </div>
        </form>
      </div>
      {/* Recent uploads */}
      <div className="rounded-lg border bg-white shadow-sm">
        <div className="border-b px-6 py-4 text-lg font-medium">
          Recent Uploads
        </div>
        <div className="p-6 overflow-x-auto">
          {statements.length === 0 ? (
            <div className="text-sm text-gray-600">No statements uploaded yet.</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th className="py-2">Filename</th>
                  <th className="py-2">Upload Date</th>
                  <th className="py-2">Transactions</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {statements.map((s) => (
                  <tr key={s.id} className="border-t">
                    <td className="py-2 font-medium">
                      <div className="flex items-center space-x-2">
                        <span className="inline-block h-4 w-4 text-red-600">
                          {/* PDF icon using SVG */}
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="currentColor"
                            viewBox="0 0 24 24"
                            className="h-4 w-4"
                          >
                            <path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6H6zm7 1.5L18.5 9H13V3.5z" />
                          </svg>
                        </span>
                        {s.filename}
                      </div>
                    </td>
                    <td className="py-2">
                      {new Date(s.created_at).toLocaleString()}
                    </td>
                    <td className="py-2">
                      {s.transactions_count} transaction
                      {s.transactions_count === 1 ? "" : "s"}
                    </td>
                    <td className="py-2">{statusBadge(s.status)}</td>
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