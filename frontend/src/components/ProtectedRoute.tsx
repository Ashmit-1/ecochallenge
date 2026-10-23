import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useMe } from "../lib/queries";
import { Loader2 } from "lucide-react";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { data: user, isLoading, isError } = useMe();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <Loader2 size={32} className="text-moss animate-spin" />
      </div>
    );
  }

  if (isError || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useMe();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <Loader2 size={32} className="text-moss animate-spin" />
      </div>
    );
  }

  if (user) {
    return <Navigate to="/challenges" replace />;
  }

  return <>{children}</>;
}
