import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRegister } from "../lib/queries";
import { AuthLayout } from "../components/Layout";
import { Card, Button, Input } from "../components/ui";
import { ApiError } from "../lib/api";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const registerMutation = useRegister();
  const navigate = useNavigate();

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!email.trim()) errs.email = "Email is required.";
    if (!displayName.trim()) errs.displayName = "Display name is required.";
    if (displayName.trim().length < 2) errs.displayName = "At least 2 characters.";
    if (password.length < 8) errs.password = "At least 8 characters.";
    if (password !== confirmPassword) errs.confirmPassword = "Passwords do not match.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    try {
      await registerMutation.mutateAsync({
        email: email.trim(),
        display_name: displayName.trim(),
        password,
      });
      navigate("/challenges", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setErrors({ form: "An account with this email or display name already exists." });
        } else {
          setErrors({ form: err.detail });
        }
      } else {
        setErrors({ form: "Something went wrong. Try again." });
      }
    }
  };

  return (
    <AuthLayout>
      <Card className="p-8">
        <h1 className="font-display text-2xl font-semibold text-ink mb-1">Join EcoChallenge</h1>
        <p className="text-ink-soft font-body mb-6">Small actions made visible.</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Display name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="name"
            required
            placeholder="How others see you"
            error={errors.displayName}
          />
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
            placeholder="you@campus.edu"
            error={errors.email}
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            placeholder="At least 8 characters"
            error={errors.password}
          />
          <Input
            label="Confirm password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            required
            placeholder="Repeat your password"
            error={errors.confirmPassword}
          />

          {errors.form && (
            <p className="text-sm text-danger font-body" role="alert">
              {errors.form}
            </p>
          )}

          <Button type="submit" disabled={registerMutation.isPending} className="w-full mt-2">
            {registerMutation.isPending ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="text-sm text-ink-soft font-body mt-6 text-center">
          Already have an account?{" "}
          <Link to="/login" className="text-moss font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </Card>
    </AuthLayout>
  );
}
