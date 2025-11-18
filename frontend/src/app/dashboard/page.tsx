"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Summary {
  total_spending: number;
  total_income: number;
  net: number;
  transaction_count: number;
  average_transaction: number;
}

interface CategorySpending {
  category: string;
  amount: number;
}

interface MonthlyTrend {
  month: string;
  spending: number;
  income: number;
}

interface TopMerchant {
  merchant: string;
  amount: number;
}

interface AnalyticsData {
  summary: Summary;
  spending_by_category: CategorySpending[];
  monthly_trends: MonthlyTrend[];
  top_merchants: TopMerchant[];
}

const COLORS = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#10b981", // green
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#6366f1", // indigo
];

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    fetchAnalytics();
  }, []);

  async function fetchAnalytics() {
    setLoading(true);
    try {
      let url = `${API}/api/dashboard/analytics`;
      const params = new URLSearchParams();
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      if (params.toString()) url += `?${params.toString()}`;

      const r = await fetch(url, {
        credentials: "include",
      });
      if (r.ok) {
        const analytics = await r.json();
        setData(analytics);
      }
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
    }
    setLoading(false);
  }

  function formatCurrency(amount: number): string {
    return `RM ${amount.toLocaleString("en-MY", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  function handleFilterApply() {
    fetchAnalytics();
  }

  function handleResetFilter() {
    setStartDate("");
    setEndDate("");
    setTimeout(() => fetchAnalytics(), 0);
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-lg text-gray-600">Loading dashboard...</div>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="mx-auto max-w-7xl p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-lg text-gray-600">No data available</div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Credit Card Dashboard</h1>
        <div className="space-x-4 text-sm">
          <Link href="/" className="text-blue-600 hover:underline">
            Upload Statements
          </Link>
          <Link href="/rules" className="text-blue-600 hover:underline">
            Rules
          </Link>
        </div>
      </div>

      {/* Date Range Filter */}
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleFilterApply}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Apply Filter
          </button>
          <button
            onClick={handleResetFilter}
            className="rounded bg-gray-200 px-4 py-2 text-sm text-gray-700 hover:bg-gray-300"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="text-sm font-medium text-gray-600">Total Spending</div>
          <div className="mt-2 text-2xl font-bold text-red-600">
            {formatCurrency(data.summary.total_spending)}
          </div>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="text-sm font-medium text-gray-600">Total Income</div>
          <div className="mt-2 text-2xl font-bold text-green-600">
            {formatCurrency(data.summary.total_income)}
          </div>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="text-sm font-medium text-gray-600">Net</div>
          <div
            className={`mt-2 text-2xl font-bold ${
              data.summary.net >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {formatCurrency(data.summary.net)}
          </div>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="text-sm font-medium text-gray-600">Transactions</div>
          <div className="mt-2 text-2xl font-bold text-blue-600">
            {data.summary.transaction_count}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            Avg: {formatCurrency(data.summary.average_transaction)}
          </div>
        </div>
      </div>

      {/* Charts Row 1: Category Spending */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Pie Chart */}
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Spending by Category</h2>
          {data.spending_by_category.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={data.spending_by_category}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry) => `${entry.category}: ${formatCurrency(entry.amount)}`}
                  labelLine={false}
                >
                  {data.spending_by_category.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[300px] items-center justify-center text-gray-500">
              No category data available
            </div>
          )}
        </div>

        {/* Category Bar Chart */}
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Category Breakdown</h2>
          {data.spending_by_category.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.spending_by_category}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="category" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Bar dataKey="amount" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[300px] items-center justify-center text-gray-500">
              No category data available
            </div>
          )}
        </div>
      </div>

      {/* Charts Row 2: Monthly Trends */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Monthly Spending Trends</h2>
        {data.monthly_trends.length > 0 ? (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={data.monthly_trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
              <Legend />
              <Line
                type="monotone"
                dataKey="spending"
                stroke="#ef4444"
                strokeWidth={2}
                name="Spending"
              />
              <Line
                type="monotone"
                dataKey="income"
                stroke="#10b981"
                strokeWidth={2}
                name="Income"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-[350px] items-center justify-center text-gray-500">
            No monthly trend data available
          </div>
        )}
      </div>

      {/* Top Merchants Table */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Top Merchants</h2>
        {data.top_merchants.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-3 font-semibold">#</th>
                  <th className="py-3 font-semibold">Merchant</th>
                  <th className="py-3 text-right font-semibold">Amount</th>
                </tr>
              </thead>
              <tbody>
                {data.top_merchants.map((merchant, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="py-3 text-gray-600">{idx + 1}</td>
                    <td className="py-3 font-medium">{merchant.merchant}</td>
                    <td className="py-3 text-right font-mono">
                      {formatCurrency(merchant.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex h-32 items-center justify-center text-gray-500">
            No merchant data available
          </div>
        )}
      </div>
    </main>
  );
}
