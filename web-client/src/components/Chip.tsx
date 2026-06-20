import type { ButtonHTMLAttributes, ReactNode } from "react";

type ChipProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  selected?: boolean;
};

export function Chip({ children, className = "", selected = false, ...props }: ChipProps) {
  return (
    <button
      className={`chip ${selected ? "chip-selected" : ""} ${className}`.trim()}
      type="button"
      aria-pressed={selected}
      {...props}
    >
      {children}
    </button>
  );
}
