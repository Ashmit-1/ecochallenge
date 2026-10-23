import { useEffect, useState, type ReactNode } from "react";
import { WifiOff, RefreshCw } from "lucide-react";
import { Button, BotanicalSprout } from "./ui";

// Contract §8: offline => branded page with a retry button. No queued mutations,
// no cached API data — just an honest message and a way back.
export function OfflineGuard({ children }: { children: ReactNode }) {
  const [offline, setOffline] = useState(
    () => typeof navigator !== "undefined" && !navigator.onLine,
  );

  useEffect(() => {
    const handleOnline = () => setOffline(false);
    const handleOffline = () => setOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (offline) return <OfflineScreen />;
  return <>{children}</>;
}

function OfflineScreen() {
  return (
    <main className="min-h-screen bg-field flex flex-col items-center justify-center px-6 py-16 text-center motion-rise">
      <div className="w-24 h-24 mb-4" aria-hidden="true">
        <BotanicalSprout />
      </div>
      <div className="w-12 h-12 rounded-full bg-mint flex items-center justify-center mb-4">
        <WifiOff size={22} strokeWidth={1.75} className="text-moss" aria-hidden="true" />
      </div>
      <h1 className="font-display text-2xl font-semibold text-ink mb-2">You're offline.</h1>
      <p className="text-ink-soft font-body max-w-[36ch] mb-8">
        Your progress is safe — come back when you're connected.
      </p>
      <Button onClick={() => window.location.reload()}>
        <RefreshCw size={18} />
        Try again
      </Button>
    </main>
  );
}