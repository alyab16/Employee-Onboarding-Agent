"use client";

import { useState } from "react";
import { EmployeeSelector } from "./components/EmployeeSelector";
import { ChatInterface } from "./components/ChatInterface";
import type { Employee } from "./types";

export default function Home() {
  const [employee, setEmployee] = useState<Employee | null>(null);

  if (!employee) {
    return <EmployeeSelector onSelect={setEmployee} />;
  }

  return (
    <div className="h-full flex flex-col">
      <ChatInterface employee={employee} onLogout={() => setEmployee(null)} />
    </div>
  );
}
