import { Trophy, Medal, Sprout } from "lucide-react";
import { useLeaderboard } from "../lib/queries";
import { Layout } from "../components/Layout";
import { Card, LeaderboardRowSkeleton, EmptyState, Chip } from "../components/ui";

export default function LeaderboardPage() {
  const { data: leaderboard, isLoading, isError } = useLeaderboard();

  if (isLoading) {
    return (
      <Layout>
        <div className="py-6 space-y-3">
          <div className="h-8 w-40 animate-pulse bg-line rounded-control" aria-hidden="true" />
          {[1, 2, 3, 4, 5].map((i) => (
            <LeaderboardRowSkeleton key={i} />
          ))}
        </div>
      </Layout>
    );
  }

  if (isError || !leaderboard) {
    return (
      <Layout>
        <EmptyState
          icon={Trophy}
          title="Could not load leaderboard"
          description="Check your connection and try again."
        />
      </Layout>
    );
  }

  if (leaderboard.entries.length === 0) {
    return (
      <Layout>
        <EmptyState
          icon={Sprout}
          title="No participants yet"
          description="Be the first to complete a challenge!"
        />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="py-6 motion-rise">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-display text-3xl font-semibold text-ink">Leaderboard</h1>
            <p className="text-ink-soft font-body mt-1">
              {leaderboard.total_participants} participant{leaderboard.total_participants !== 1 ? "s" : ""}
            </p>
          </div>
          <Chip color="sun" icon={Trophy}>
            Your rank: <span className="tabular-nums font-semibold">#{leaderboard.current_user_rank}</span>
          </Chip>
        </div>

        <div className="flex flex-col gap-2">
          {leaderboard.entries.map((entry) => {
            const isTop3 = entry.rank <= 3;
            const RankIcon = entry.rank === 1 ? Trophy : entry.rank <= 3 ? Medal : null;

            return (
              <Card
                key={entry.user_id}
                className={`flex items-center gap-4 py-3 px-5 ${
                  entry.is_current_user ? "bg-mint border-moss/20" : ""
                }`}
              >
                {/* Rank */}
                <div className="w-10 flex items-center justify-center shrink-0">
                  {RankIcon ? (
                    <RankIcon
                      size={22}
                      className={
                        entry.rank === 1
                          ? "text-sun"
                          : entry.rank === 2
                            ? "text-ink-soft"
                            : "text-clay"
                      }
                    />
                  ) : (
                    <span className="font-display text-xl font-semibold text-ink tabular-nums">
                      {entry.rank}
                    </span>
                  )}
                </div>

                {/* Name */}
                <div className="flex-1 min-w-0">
                  <p
                    className={`font-body font-medium truncate ${
                      entry.is_current_user ? "text-moss" : "text-ink"
                    }`}
                  >
                    {entry.display_name}
                    {entry.is_current_user && (
                      <span className="ml-2 text-xs font-normal text-moss/70">You</span>
                    )}
                  </p>
                  <p className="text-xs text-ink-soft font-body">
                    {entry.challenges_completed} challenge{entry.challenges_completed !== 1 ? "s" : ""}
                  </p>
                </div>

                {/* Points */}
                <div className="text-right shrink-0">
                  <p className="font-display text-lg font-semibold text-ink tabular-nums">
                    {entry.points_total}
                  </p>
                  <p className="text-xs text-ink-soft font-body">pts</p>
                </div>
              </Card>
            );
          })}
        </div>

        <p className="text-xs text-ink-soft font-body mt-6 text-center">
          Tied scores share the same rank.
        </p>
      </div>
    </Layout>
  );
}
