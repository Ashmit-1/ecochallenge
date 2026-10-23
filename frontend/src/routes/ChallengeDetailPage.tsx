import { useState, useRef, useEffect, type ChangeEvent } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Bike,
  Recycle,
  Sprout,
  Repeat,
  Sparkles,
  Upload,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Info,
  Award,
} from "lucide-react";
import { useChallengeDetail, useSubmitEvidence } from "../lib/queries";
import { Layout } from "../components/Layout";
import { Card, Chip, Button, Skeleton } from "../components/ui";
import type { Badge } from "../types";

const iconMap: Record<string, typeof Bike> = {
  bike: Bike,
  recycle: Recycle,
  sprout: Sprout,
  repeat: Repeat,
  sparkles: Sparkles,
};

export default function ChallengeDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { data: challenge, isLoading, isError } = useChallengeDetail(slug!);
  const submitMutation = useSubmitEvidence(slug!);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState("");
  const [result, setResult] = useState<{
    status: "approved" | "rejected";
    points: number;
    reason: string | null;
    newBadges: Badge[];
  } | null>(null);

  useEffect(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  if (!slug) return null;

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 6 * 1024 * 1024) {
      setSubmitError("Photo must be under 6 MB.");
      return;
    }
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setSubmitError("");
    setResult(null);
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;
    setSubmitError("");
    try {
      const res = await submitMutation.mutateAsync(selectedFile);
      setResult({
        status: res.submission.status as "approved" | "rejected",
        points: res.submission.points_awarded,
        reason: res.submission.verification.reason,
        newBadges: res.new_badges,
      });
    } catch (err: unknown) {
      const apiErr = err as { status?: number; detail?: string };
      if (apiErr?.status === 409) setSubmitError("This exact photo was already submitted. Take a new one.");
      else if (apiErr?.status === 413) setSubmitError("File too large (max 6 MB).");
      else if (apiErr?.status === 415) setSubmitError("Not a valid image. Use JPEG, PNG, or WebP at least 200×200 px.");
      else if (apiErr?.status === 429) setSubmitError(apiErr.detail || "Cooldown active. Wait before submitting again.");
      else if (apiErr?.status === 502) setSubmitError("Verification service unavailable. No points awarded — try again later.");
      else setSubmitError(apiErr?.detail || "Submission failed. Try again.");
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="py-6 space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-48 w-full rounded-card" />
        </div>
      </Layout>
    );
  }

  if (isError || !challenge) {
    return (
      <Layout>
        <div className="py-6">
          <p className="text-danger">Challenge not found.</p>
          <Link to="/challenges" className="text-moss underline mt-4 inline-block">
            Back to challenges
          </Link>
        </div>
      </Layout>
    );
  }

  const Icon = iconMap[challenge.icon] ?? Sprout;

  return (
    <Layout>
      <div className="py-6">
        <Link
          to="/challenges"
          className="inline-flex items-center gap-1.5 text-ink-soft hover:text-moss font-body text-sm mb-6 transition-colors"
        >
          <ArrowLeft size={16} />
          All challenges
        </Link>

        <div className="flex items-start gap-4 mb-6">
          <div className="flex items-center justify-center w-14 h-14 rounded-full bg-mint text-moss shrink-0">
            <Icon size={28} strokeWidth={1.75} />
          </div>
          <div>
            <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink mb-1">
              {challenge.title}
            </h1>
            <p className="text-ink-soft font-body">{challenge.tagline}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-8">
          <Chip color="sun">+{challenge.points} pts</Chip>
          <Chip color="leaf">~{challenge.co2_saved_grams}g CO₂ estimated</Chip>
          {challenge.cooldown_hours > 0 && (
            <Chip color="mint" icon={Clock}>
              {challenge.cooldown_hours}h cooldown
            </Chip>
          )}
          {challenge.times_completed > 0 && (
            <Chip color="moss">Completed {challenge.times_completed}×</Chip>
          )}
        </div>

        <Card className="mb-6">
          <h2 className="font-display text-lg font-semibold text-ink mb-3">About this challenge</h2>
          <p className="text-ink font-body leading-relaxed mb-4">{challenge.description}</p>

          <h3 className="font-body font-semibold text-ink mb-2">Instructions</h3>
          <ol className="list-decimal list-inside text-ink-soft font-body space-y-1 mb-4">
            {challenge.instructions.split("\n").map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ol>

          <h3 className="font-body font-semibold text-ink mb-2">What your photo must show</h3>
          <p className="text-ink-soft font-body">{challenge.evidence_requirements}</p>
        </Card>

        {/* Submission section */}
        <Card className="mb-6">
          <h2 className="font-display text-lg font-semibold text-ink mb-4">Submit evidence</h2>

          {!challenge.can_submit && (
            <div className="flex items-start gap-3 p-4 bg-sun/10 rounded-control mb-4">
              <Clock size={20} className="text-sun shrink-0 mt-0.5" />
              <div>
                <p className="font-body text-ink font-medium">Cooldown active</p>
                <p className="font-body text-ink-soft text-sm">
                  You can submit this challenge again after{" "}
                  {challenge.cooldown_ends_at
                    ? new Date(challenge.cooldown_ends_at).toLocaleString()
                    : "the cooldown period ends"}
                  .
                </p>
              </div>
            </div>
          )}

          {!result && (
            <>
              <div
                className={`border-2 border-dashed rounded-card p-8 text-center mb-4 transition-colors ${
                  previewUrl ? "border-moss/30 bg-mint/10" : "border-line hover:border-moss/30"
                }`}
              >
                {previewUrl ? (
                  <div className="space-y-4">
                    <img
                      src={previewUrl}
                      alt="Selected evidence"
                      className="max-h-64 mx-auto rounded-control object-contain"
                    />
                    <p className="text-sm text-ink-soft font-body">{selectedFile?.name}</p>
                    <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
                      Choose different photo
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Upload size={32} className="mx-auto text-leaf" strokeWidth={1.5} />
                    <p className="font-body text-ink">Select a photo of your completed challenge</p>
                    <p className="font-body text-ink-soft text-sm">
                      JPEG, PNG, or WebP · At least 200×200 px · Max 6 MB
                    </p>
                    <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
                      Choose photo
                    </Button>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  className="hidden"
                  aria-label="Upload evidence photo"
                />
              </div>

              {submitError && (
                <p className="text-sm text-danger font-body mb-4" role="alert">
                  {submitError}
                </p>
              )}

              <div className="flex items-start gap-2 p-3 bg-mint/30 rounded-control mb-4">
                <Info size={16} className="text-moss shrink-0 mt-0.5" />
                <p className="text-sm text-ink-soft font-body">
                  Your photo will be checked by AI. This usually takes 2–6 seconds. Approval means
                  the photo looked consistent — it is not proof the activity happened.
                </p>
              </div>

              <Button
                onClick={handleSubmit}
                disabled={!selectedFile || !challenge.can_submit || submitMutation.isPending}
                className="w-full"
              >
                {submitMutation.isPending ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Checking your photo…
                  </>
                ) : (
                  <>
                    <Upload size={18} />
                    Submit for verification
                  </>
                )}
              </Button>
            </>
          )}

          {/* Result state */}
          {result && (
            <div aria-live="polite">
              {result.status === "approved" ? (
                <div className="text-center py-4 space-y-4">
                  <CheckCircle2 size={48} className="mx-auto text-moss" strokeWidth={1.5} />
                  <h3 className="font-display text-xl font-semibold text-ink">Approved</h3>
                  <p className="font-body text-ink-soft">
                    You earned{" "}
                    <span className="font-semibold text-ink tabular-nums">{result.points} points</span>.
                  </p>
                  {result.reason && (
                    <p className="font-body text-ink-soft text-sm italic">"{result.reason}"</p>
                  )}
                  {result.newBadges.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <p className="font-body text-sm text-moss font-medium">New badge unlocked!</p>
                      {result.newBadges.map((badge) => (
                        <Card key={badge.key} className="inline-flex items-center gap-3 p-3">
                          <Award size={24} className="text-sun" />
                          <div className="text-left">
                            <p className="font-display font-semibold text-ink">{badge.name}</p>
                            <p className="font-body text-sm text-ink-soft">{badge.description}</p>
                          </div>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-4 space-y-4">
                  <XCircle size={48} className="mx-auto text-clay" strokeWidth={1.5} />
                  <h3 className="font-display text-xl font-semibold text-ink">Not approved</h3>
                  <p className="font-body text-ink-soft">
                    {result.reason || "The photo did not match what we expected."}
                  </p>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setResult(null);
                      setSelectedFile(null);
                      setPreviewUrl(null);
                    }}
                  >
                    Try again with a new photo
                  </Button>
                </div>
              )}
              <div className="pt-4">
                <Button onClick={() => navigate("/challenges")} className="w-full">
                  Back to challenges
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}
