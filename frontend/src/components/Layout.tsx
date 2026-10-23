import { type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Sprout, Trophy, User, LogOut, Loader2 } from "lucide-react";
import { useMe, useLogout, queryKeys } from "../lib/queries";
import { useQueryClient } from "@tanstack/react-query";
import { Chip } from "./ui";

const navItems = [
  { to: "/challenges", label: "Challenges", icon: Sprout },
  { to: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { to: "/profile", label: "Profile", icon: User },
];

function NavItem({ to, label, icon: Icon }: { to: string; label: string; icon: typeof Sprout }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex flex-col items-center gap-1 px-3 py-2 rounded-control min-w-[60px] transition-colors font-body text-xs ${
          isActive ? "text-moss" : "text-ink-soft hover:text-ink"
        }`
      }
    >
      <Icon size={22} strokeWidth={isActive ? 2 : 1.75} />
      <span>{label}</span>
    </NavLink>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { data: user } = useMe();
  const logoutMutation = useLogout();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logoutMutation.mutateAsync();
      queryClient.clear();
      navigate("/login");
    } catch {
      // ignore
    }
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col">
      {/* Desktop top nav */}
      <header className="hidden md:flex items-center justify-between px-8 py-4 max-w-[1120px] mx-auto w-full">
        <div className="flex items-center gap-3">
          <Sprout size={28} className="text-moss" strokeWidth={1.75} />
          <span className="font-display text-xl font-semibold text-ink">EcoChallenge</span>
        </div>
        <nav className="flex items-center gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-4 py-2 rounded-control font-body text-sm font-medium transition-colors ${
                  isActive ? "bg-mint text-moss" : "text-ink-soft hover:text-ink hover:bg-mint/40"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          {user && (
            <Chip color="sun" icon={Trophy}>
              <span className="tabular-nums">{user.points_total}</span> pts
            </Chip>
          )}
          <button
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
            className="p-2 text-ink-soft hover:text-danger transition-colors rounded-control min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Log out"
          >
            {logoutMutation.isPending ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <LogOut size={18} strokeWidth={1.75} />
            )}
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 w-full max-w-[1120px] mx-auto px-5 md:px-8 pb-24 md:pb-8">
        {children}
      </main>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-line flex items-center justify-around py-2 px-4 z-50">
        {navItems.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>
    </div>
  );
}

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-paper flex flex-col items-center justify-center px-5 py-12">
      <div className="flex items-center gap-3 mb-8">
        <Sprout size={36} className="text-moss" strokeWidth={1.5} />
        <span className="font-display text-3xl font-semibold text-ink">EcoChallenge</span>
      </div>
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
