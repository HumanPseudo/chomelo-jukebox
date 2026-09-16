import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  accent?: boolean;
  live?: boolean;
}

export function Panel({ children, accent, live, className = "", ...rest }: PanelProps) {
  const variant = live ? "panel--live" : accent ? "panel--accent" : "";
  return (
    <div className={`panel ${variant} ${className}`} {...rest}>
      {children}
    </div>
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
  size?: "md" | "sm";
}

export function Button({ variant = "primary", size = "md", className = "", ...rest }: ButtonProps) {
  const sizeClass = size === "sm" ? "btn--sm" : "";
  return <button className={`btn btn--${variant} ${sizeClass} ${className}`} {...rest} />;
}

export function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} />;
}

export function SignalDot({ state = "idle" }: { state?: "idle" | "live" | "rec" }) {
  const variant = state === "live" ? "signal-dot--live" : state === "rec" ? "signal-dot--rec" : "";
  return <span className={`signal-dot ${variant}`} />;
}

export function Tag({ children, live }: { children: ReactNode; live?: boolean }) {
  return <span className={`tag ${live ? "tag--live" : ""}`}>{children}</span>;
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div style={{ padding: "32px 0", color: "var(--dim)", fontFamily: "var(--font-mono)" }}>
      {children}
    </div>
  );
}
