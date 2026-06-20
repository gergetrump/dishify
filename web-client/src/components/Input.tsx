import type { InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
};

export function Input({ className = "", id, label, ...props }: InputProps) {
  const inputId = id ?? props.name;

  return (
    <label className="field" htmlFor={inputId}>
      <span>{label}</span>
      <input id={inputId} className={`input ${className}`.trim()} {...props} />
    </label>
  );
}
