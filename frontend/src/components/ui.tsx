import { type ButtonHTMLAttributes, type ReactNode } from "react";
import { type LucideIcon } from "lucide-react";

// --- Button ---

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
  icon?: LucideIcon;
}

export function Button({
  variant = "primary",
  icon: Icon,
  children,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 font-body font-medium transition-all duration-200 ease-[cubic-bezier(.2,.8,.2,1)] min-h-[44px] min-w-[44px] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss";
  const variants = {
    primary:
      "bg-moss text-white rounded-control px-5 py-2.5 hover:bg-moss/90 active:scale-[0.98] disabled:bg-line disabled:text-ink-soft",
    secondary:
      "bg-surface text-moss border border-line rounded-control px-5 py-2.5 hover:border-moss/30 hover:bg-mint/30 active:scale-[0.98] disabled:opacity-50",
    danger:
      "bg-danger text-white rounded-control px-5 py-2.5 hover:bg-danger/90 active:scale-[0.98] disabled:opacity-50",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {Icon && <Icon size={18} strokeWidth={1.75} />}
      {children}
    </button>
  );
}

// --- Card ---

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  as?: "div" | "a" | "button";
  href?: string;
}

export function Card({ children, className = "", onClick, as: Tag = "div", href }: CardProps) {
  const base =
    "bg-surface rounded-card border border-line shadow-card p-5 transition-all duration-200 ease-[cubic-bezier(.2,.8,.2,1)]";
  const interactive = onClick || href
    ? "cursor-pointer hover:-translate-y-0.5 hover:border-moss/20"
    : "";

  if (Tag === "a" && href) {
    return (
      <a href={href} className={`${base} ${interactive} block ${className}`} onClick={onClick}>
        {children}
      </a>
    );
  }
  if (Tag === "button") {
    return (
      <button className={`${base} ${interactive} w-full text-left ${className}`} onClick={onClick}>
        {children}
      </button>
    );
  }
  return (
    <div className={`${base} ${interactive} ${className}`} onClick={onClick} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined}>
      {children}
    </div>
  );
}

// --- Chip ---

interface ChipProps {
  children: ReactNode;
  color?: "sun" | "mint" | "clay" | "leaf" | "moss";
  icon?: LucideIcon;
  className?: string;
}

export function Chip({ children, color = "mint", icon: Icon, className = "" }: ChipProps) {
  const colors = {
    sun: "bg-sun/15 text-ink",
    mint: "bg-mint text-ink",
    clay: "bg-clay/15 text-clay",
    leaf: "bg-leaf/20 text-ink",
    moss: "bg-moss/10 text-moss",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-sm font-body font-medium px-3 py-1 rounded-full ${colors[color]} ${className}`}
    >
      {Icon && <Icon size={14} strokeWidth={1.75} />}
      {children}
    </span>
  );
}

// --- IconChip ---

interface IconChipProps {
  icon: LucideIcon;
  className?: string;
}

export function IconChip({ icon: Icon, className = "" }: IconChipProps) {
  return (
    <div
      className={`flex items-center justify-center w-10 h-10 rounded-full bg-mint text-moss shrink-0 ${className}`}
    >
      <Icon size={20} strokeWidth={1.75} />
    </div>
  );
}

// --- Skeleton ---

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-line rounded-control ${className}`} aria-hidden="true" />;
}

// Shaped skeletons matching real card anatomy (design.md §5)

export function ChallengeCardSkeleton() {
  return (
    <div className="bg-surface rounded-card border border-line shadow-card p-5" aria-hidden="true">
      <div className="flex items-start gap-4">
        <Skeleton className="w-10 h-10 rounded-full shrink-0" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function LeaderboardRowSkeleton() {
  return (
    <div className="bg-surface rounded-card border border-line p-4 flex items-center gap-4" aria-hidden="true">
      <Skeleton className="w-8 h-8 rounded-full" />
      <Skeleton className="h-5 w-32 flex-1" />
      <Skeleton className="h-5 w-16" />
    </div>
  );
}

export function ProfileSkeleton() {
  return (
    <div className="space-y-6 py-6" aria-hidden="true">
      <div className="flex items-center gap-4">
        <Skeleton className="w-16 h-16 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-20 rounded-card" />
        ))}
      </div>
    </div>
  );
}

// --- EmptyState ---

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-5 text-center motion-rise">
      <div className="w-24 h-24 mb-4" aria-hidden="true">
        <BotanicalSprout />
      </div>
      <div className="w-10 h-10 rounded-full bg-mint flex items-center justify-center mb-3">
        <Icon size={20} strokeWidth={1.75} className="text-moss" />
      </div>
      <h3 className="font-display text-xl font-semibold text-ink mb-2">{title}</h3>
      <p className="text-ink-soft font-body max-w-[40ch] mb-6">{description}</p>
      {action}
    </div>
  );
}

// Hand-drawn botanical accent (design.md §3): 1.5px stroke, rounded caps

export function BotanicalSprout({ small = false }: { small?: boolean }) {
  const stroke = 1.5;
  const size = small ? 40 : 96;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 96 96"
      width={size}
      height={size}
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M48 82 C48 62 48 52 44 40"
        stroke="#6FA98A"
        strokeWidth={stroke + 0.7}
        strokeLinecap="round"
      />
      <path
        d="M44 50 C30 44 24 30 30 16 C40 22 46 36 44 50 Z"
        fill="#DCEBE2"
        stroke="#2F6B4F"
        strokeWidth={stroke}
        strokeLinejoin="round"
      />
      <path
        d="M45 44 C58 38 66 24 62 10 C52 14 46 30 45 44 Z"
        fill="#6FA98A"
        stroke="#2F6B4F"
        strokeWidth={stroke}
        strokeLinejoin="round"
      />
      <path d="M34 84 C42 80 54 80 62 84" stroke="#E2E0D6" strokeWidth={stroke + 0.5} strokeLinecap="round" />
      <path d="M40 88 C44 86 52 86 56 88" stroke="#E2E0D6" strokeWidth={stroke + 0.5} strokeLinecap="round" />
    </svg>
  );
}

// --- Input ---

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, id, className = "", ...props }: InputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={inputId} className="text-sm font-body font-medium text-ink">
        {label}
      </label>
      <input
        id={inputId}
        className={`w-full px-4 py-2.5 bg-surface border rounded-control font-body text-ink placeholder:text-ink-soft/50 focus:outline-none focus:ring-2 focus:ring-moss focus:ring-offset-2 focus:ring-offset-paper min-h-[44px] transition-colors ${
          error ? "border-danger" : "border-line"
        }`}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${inputId}-error`} className="text-sm text-danger font-body" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
