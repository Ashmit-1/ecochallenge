import { useState, type FormEvent } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useLogin } from "../lib/queries";
import { AuthLayout } from "../components/Layout";
import { Card, Button, Input } from "../components/ui";
import { ApiError } from "../lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const loginMutation = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/challenges";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (loginMutation.isPending) return; // double-submit guard (contract §5)
    setError("");
    if (!email.trim() || !password) {
      setError("Email and password are required.");
      return;
    }
    try {
      await loginMutation.mutateAsync({ email: email.trim(), password });
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || "Invalid credentials.");
      } else {
        setError("Something went wrong. Try again.");
      }
    }
  };

  return (
    <AuthLayout>
      <Card className="p-8">
        <h1 className="font-display text-2xl font-semibold text-ink mb-1">Welcome back</h1>
        <p className="text-ink-soft font-body mb-6">Sign in to continue your eco journey.</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
            placeholder="you@campus.edu"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            placeholder="Your password"
          />

          {error && (
            <p className="text-sm text-danger font-body" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" disabled={loginMutation.isPending} className="w-full mt-2">
            {loginMutation.isPending ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="text-sm text-ink-soft font-body mt-6 text-center">
          New here?{" "}
          <Link to="/register" className="text-moss font-medium hover:underline">
            Create an account
          </Link>
        </p>
      </Card>
    </AuthLayout>
  );
}
