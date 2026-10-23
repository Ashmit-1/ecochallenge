import { useState } from "react";
import {
  Sprout,
  Footprints,
  Award,
  Trophy,
  CloudOff,
  Compass,
  Star,
  Target,
  Leaf,
  TrendingUp,
  Pencil,
  Check,
  X,
} from "lucide-react";
import { useProfile, useUpdateDisplayName } from "../lib/queries";
import { Layout } from "../components/Layout";
import { Card, Chip, ProfileSkeleton, EmptyState } from "../components/ui";
import { Button, Input } from "../components/ui";

const badgeIconMap: Record<string, typeof Sprout> = {
  sprout: Sprout,
  footprints: Footprints,
  award: Award,
  trophy: Trophy,
  "cloud-off": CloudOff,
  compass: Compass,
};

export default function ProfilePage() {
  const { data: profile, isLoading, isError } = useProfile();
  const updateName = useUpdateDisplayName();
  const [editing, setEditing] = useState(false);
  const [newName, setNewName] = useState("");

  const startEdit = () => {
    if (profile) setNewName(profile.display_name);
    setEditing(true);
  };

  const saveEdit = async () => {
    if (!newName.trim()) return;
    try {
      await updateName.mutateAsync(newName.trim());
      setEditing(false);
    } catch {
      // error handled by mutation
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="py-6 space-y-4">
          <ProfileSkeleton />
        </div>
      </Layout>
    );
  }

  if (isError || !profile) {
    return (
      <Layout>
        <EmptyState icon={Star} title="Could not load profile" description="Try refreshing the page." />
      </Layout>
    );
  }

  const co2Kg = (profile.co2_saved_grams / 1000).toFixed(1);

  return (
    <Layout>
      <div className="py-6 motion-rise">
        <div className="flex items-start justify-between mb-8">
          <div>
            {editing ? (
              <div className="flex items-center gap-2">
                <Input
                  label="Display name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-48"
                />
                <Button onClick={saveEdit} disabled={updateName.isPending} className="mt-5">
                  <Check size={16} />
                </Button>
                <Button variant="secondary" onClick={() => setEditing(false)} className="mt-5">
                  <X size={16} />
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="font-display text-3xl font-semibold text-ink">
                  {profile.display_name}
                </h1>
                <button
                  onClick={startEdit}
                  className="p-2 text-ink-soft hover:text-moss transition-colors rounded-control min-w-[44px] min-h-[44px] flex items-center justify-center"
                  aria-label="Edit display name"
                >
                  <Pencil size={16} strokeWidth={1.75} />
                </button>
              </div>
            )}
            <p className="text-ink-soft font-body mt-1">{profile.email}</p>
            <p className="text-ink-soft font-body text-sm mt-1">
              Member since {new Date(profile.member_since).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <div className="flex items-center gap-2 mb-2">
              <Trophy size={18} className="text-sun" />
              <span className="text-sm font-body text-ink-soft">Points</span>
            </div>
            <p className="font-display text-2xl font-semibold text-ink tabular-nums">
              {profile.points_total}
            </p>
          </Card>
          <Card>
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={18} className="text-moss" />
              <span className="text-sm font-body text-ink-soft">Rank</span>
            </div>
            <p className="font-display text-2xl font-semibold text-ink tabular-nums">
              #{profile.rank}
              <span className="text-sm font-body text-ink-soft ml-1">of {profile.total_participants}</span>
            </p>
          </Card>
          <Card>
            <div className="flex items-center gap-2 mb-2">
              <Target size={18} className="text-leaf" />
              <span className="text-sm font-body text-ink-soft">Approved</span>
            </div>
            <p className="font-display text-2xl font-semibold text-ink tabular-nums">
              {profile.submissions_approved}
              <span className="text-sm font-body text-ink-soft">/{profile.submissions_total}</span>
            </p>
          </Card>
          <Card>
            <div className="flex items-center gap-2 mb-2">
              <Leaf size={18} className="text-leaf" />
              <span className="text-sm font-body text-ink-soft">CO₂ saved</span>
            </div>
            <p className="font-display text-2xl font-semibold text-ink tabular-nums">
              ~{co2Kg} kg
            </p>
          </Card>
        </div>

        <p className="text-xs text-ink-soft font-body mb-8 flex items-center gap-1">
          <CloudOff size={12} />
          CO₂ savings are estimates based on challenge assumptions, not measured values.
        </p>

        {/* Badges */}
        <h2 className="font-display text-xl font-semibold text-ink mb-4">Badges</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {profile.badges.map((badge) => {
            const BIcon = badgeIconMap[badge.icon] ?? Award;
            const progress = badge.target > 0 ? Math.min(badge.current / badge.target, 1) : 0;

            return (
              <Card key={badge.key} className={`relative ${badge.earned ? "badge-unlock" : "opacity-60"}`}>
                <div className="flex items-start gap-3">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                      badge.earned ? "bg-sun/15 text-sun" : "bg-line text-ink-soft"
                    }`}
                  >
                    <BIcon size={20} strokeWidth={1.75} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-display font-semibold text-ink text-sm">{badge.name}</h3>
                    <p className="font-body text-xs text-ink-soft mt-0.5">{badge.description}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-line rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            badge.earned ? "bg-sun" : "bg-leaf"
                          }`}
                          style={{ width: `${progress * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-body text-ink-soft tabular-nums">
                        {badge.current}/{badge.target}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Stats summary */}
        <Card>
          <h2 className="font-display text-lg font-semibold text-ink mb-3">Activity summary</h2>
          <div className="space-y-2 font-body text-sm">
            <div className="flex justify-between">
              <span className="text-ink-soft">Distinct challenges completed</span>
              <span className="text-ink font-medium tabular-nums">{profile.challenges_completed}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-soft">Submissions rejected</span>
              <span className="text-ink font-medium tabular-nums">{profile.submissions_rejected}</span>
            </div>
          </div>
        </Card>
      </div>
    </Layout>
  );
}
