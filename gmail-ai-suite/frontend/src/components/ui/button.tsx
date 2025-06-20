import * as React from "react";
import { cn } from "../lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", ...props }, ref) => {
    const variantClass =
      variant === "default"
        ? "bg-gray-900 text-white hover:bg-gray-800 active:bg-gray-700"
        : "border border-gray-300 bg-white text-gray-900 hover:bg-gray-50";

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium",
          variantClass,
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
