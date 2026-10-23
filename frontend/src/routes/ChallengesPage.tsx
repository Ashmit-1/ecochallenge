import { Link } from "react-router-dom";
import { Bike, Recycle, Sprout, Repeat, Sparkles, Clock, Leaf } from "lucide-react";
import { useChallenges } from "../lib/queries";
import { Layout } from "../components/Layout";
import { Card, Chip, IconChip, ChallengeCardSkeleton, EmptyState } from "../components/ui";
import type { Category } from "../types";

const iconMap: Record<string, typeof Bike> = {
  bike: Bike,
  recycle: Recycle,
  sprout: Sprout,
  repeat: Repeat,
  sparkles: Sparkles,
};

const categoryLabels: Record<Category, string> = {
  transport: "Transport",
  waste: "Waste",
  nature: "Nature",
  reuse: "Reuse",
  community: "Community",
};

function formatCooldown(iso: string | null): string | null {
  if (!iso) return null;
  const ends = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = ends - now;
  if (diffMs <= 0) return null;
  const hours = Math.floor(diffMs / 3_600_000);
  const minutes = Math.floor((diffMs % 3_600_000) / 60_000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export default function ChallengesPage() {
  const { data: challenges, isLoading, isError } = useChallenges();

  return (
    <Layout>
      <div className="py-6 motion-rise">
        <h1 className="font-display text-3xl font-semibold text-ink mb-2">Challenges</h1>
        <p className="text-ink-soft font-body mb-8 max-w-[60ch]">
          Pick one, do it in the real world, prove it with a photo.
        </p>

        {isLoading && (
          <div className="flex flex-col gap-4">
            {[1, 2, 3].map((i) => (
              <ChallengeCardSkeleton key={i} />
            ))}
          </div>
        )}

        {isError && (
          <EmptyState
            icon={Sprout}
            title="Could not load challenges"
            description="Check your connection and try again."
          />
        )}

        {!isLoading && !isError && challenges && challenges.length === 0 && (
          <EmptyState
            icon={Leaf}
            title="No challenges yet"
            description="New challenges will appear here soon."
          />
        )}

        {!isLoading && challenges && challenges.length > 0 && (
          <div className="flex flex-col gap-4">
            {challenges.map((challenge) => {
              const Icon = iconMap[challenge.icon] ?? Sprout;
              const cooldownText = formatCooldown(challenge.cooldown_ends_at);

              return (
                <Link
                  key={challenge.id}
                  to={`/challenges/${challenge.slug}`}
                  className="block group"
                >
                  <Card className="card-hover">
                    <div className="flex items-start gap-4">
                      <IconChip icon={Icon} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-3 mb-1">
                          <h2 className="font-display text-lg font-semibold text-ink leading-tight">
                            {challenge.title}
                          </h2>
                          <Chip color="sun">+{challenge.points} pts</Chip>
                        </div>
                        <p className="text-ink-soft font-body text-sm mb-3 line-clamp-1">
                          {challenge.tagline}
                        </p>
                        <div className="flex flex-wrap items-center gap-2">
                          <Chip color="leaf">{categoryLabels[challenge.category]}</Chip>
                          <Chip color="mint" icon={Leaf}>
                            ~{challenge.co2_saved_grams}g CO₂
                          </Chip>
                          {challenge.times_completed > 0 && (
                            <Chip color="moss">
                              Done {challenge.times_completed}×
                            </Chip>
                          )}
                          {cooldownText && (
                            <Chip color="sun" icon={Clock}>
                              Again in {cooldownText}
                            </Chip>
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
