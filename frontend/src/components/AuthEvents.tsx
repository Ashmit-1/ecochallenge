import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { setUnauthorizedHandler } from "../lib/api";

// Wires the fetch layer's 401 signal to the router (contract §2.4).
// Registered once at app root; the handler reads window.location.pathname at
// call time, so it is always current — and it refuses to redirect when we are
// already on an auth page, which is what made the previous hard-navigation
// implementation loop forever.
export function AuthEvents() {
  const navigate = useNavigate();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      const path = window.location.pathname;
      if (path !== "/login" && path !== "/register") {
        navigate("/login", { replace: true });
      }
    });
    return () => setUnauthorizedHandler(null);
  }, [navigate]);

  return null;
}