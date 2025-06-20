import * as React from "react";
import { cn } from "../lib/utils";

type SelectCtx = {
  value: string;
  onValueChange: (v: string) => void;
};
const SelectContext = React.createContext<SelectCtx | null>(null);

export function Select({
  value,
  onValueChange,
  children,
}: {
  value: string;
  onValueChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <SelectContext.Provider value={{ value, onValueChange }}>
      <div className="relative inline-block w-full">{children}</div>
    </SelectContext.Provider>
  );
}

export function SelectTrigger({
  className,
}: React.ComponentProps<"button">) {
  const ctx = React.useContext(SelectContext)!;
  return (
    <button
      className={cn(
        "flex w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm",
        className
      )}
    >
      <span>{ctx.value}</span>
      <svg
        className="h-4 w-4 opacity-70"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </button>
  );
}

export function SelectContent({
  children,
}: React.ComponentProps<"div">) {
  return (
    <div className="absolute z-10 mt-1 w-full rounded-md border bg-white shadow">
      {children}
    </div>
  );
}

export function SelectItem({
  value,
  children,
}: {
  value: string;
  children: React.ReactNode;
}) {
  const ctx = React.useContext(SelectContext)!;
  return (
    <div
      className="cursor-pointer px-3 py-2 text-sm hover:bg-gray-100"
      onClick={() => ctx.onValueChange(value)}
    >
      {children}
    </div>
  );
}

export const SelectValue = ({ placeholder }: { placeholder?: string }) => (
  <span className="opacity-50">{placeholder}</span>
);
