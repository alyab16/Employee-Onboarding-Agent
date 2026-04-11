"use client";

import { useEffect, useState } from "react";
import type { Employee } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  onSelect: (employee: Employee) => void;
}

const DEPT_STYLES: Record<string, string> = {
  Engineering: "text-blue-600 bg-blue-50",
  Sales: "text-emerald-600 bg-emerald-50",
  Marketing: "text-orange-600 bg-orange-50",
  Finance: "text-violet-600 bg-violet-50",
  HR: "text-rose-600 bg-rose-50",
};

export function EmployeeSelector({ onSelect }: Props) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/admin/employees`)
      .then((r) => r.json())
      .then((data) => setEmployees(data.employees))
      .catch(() =>
        setFetchError("Could not reach the backend. Is it running on port 8000?"),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-10">
          <p className="text-xs font-semibold tracking-widest text-stone-400 uppercase mb-2">
            Onboarding Portal
          </p>
          <h1 className="text-3xl font-bold text-stone-900 tracking-tight">
            Welcome to Acme Corp
          </h1>
          <p className="text-stone-500 mt-2 text-sm leading-relaxed">
            Select your profile below to start your onboarding journey with our
            AI assistant.
          </p>
        </div>

        {/* Tech badges */}
        <div className="flex gap-1.5 mb-6">
          {["LangGraph", "FastMCP", "OpenAI / Ollama", "Next.js"].map((b) => (
            <span
              key={b}
              className="text-[10px] px-2 py-0.5 rounded bg-stone-100 text-stone-500 font-mono"
            >
              {b}
            </span>
          ))}
        </div>

        {/* Employee list */}
        <div className="space-y-2">
          {loading && (
            <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
              <div className="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-stone-400">Connecting to backend...</p>
            </div>
          )}

          {fetchError && (
            <div className="bg-white rounded-xl border border-red-200 p-6 text-center">
              <p className="font-medium text-stone-800 text-sm mb-1">
                Backend unavailable
              </p>
              <p className="text-stone-500 text-xs mb-4">{fetchError}</p>
              <code className="text-xs bg-stone-50 text-stone-600 px-3 py-1.5 rounded-lg border border-stone-200 font-mono">
                cd backend && uv run uvicorn main:app --reload
              </code>
            </div>
          )}

          {!loading &&
            !fetchError &&
            employees.map((emp) => (
              <button
                key={emp.id}
                onClick={() => onSelect(emp)}
                className="group w-full bg-white rounded-xl border border-stone-200 px-4 py-3.5 text-left
                  hover:border-stone-300 hover:shadow-sm active:scale-[0.99] transition-all flex items-center gap-3.5"
              >
                <div className="w-9 h-9 rounded-lg bg-stone-800 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                  {emp.name
                    .split(" ")
                    .map((n: string) => n[0])
                    .join("")}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-stone-900 text-sm">
                    {emp.name}
                  </p>
                  <p className="text-xs text-stone-400 mt-0.5">
                    {emp.role} · {emp.level}
                  </p>
                </div>
                <span
                  className={`flex-shrink-0 text-[11px] px-2 py-0.5 rounded-md font-medium
                    ${DEPT_STYLES[emp.department] ?? "text-stone-500 bg-stone-50"}`}
                >
                  {emp.department}
                </span>
              </button>
            ))}
        </div>

        <p className="text-center text-[11px] text-stone-400 mt-6">
          Mock employees — no credentials required
        </p>
      </div>
    </div>
  );
}
