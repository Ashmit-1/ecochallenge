import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { ProtectedRoute, PublicOnlyRoute } from "./components/ProtectedRoute";
import { AuthEvents } from "./components/AuthEvents";
import { OfflineGuard } from "./components/OfflineGuard";

const LoginPage = lazy(() => import("./routes/LoginPage"));
const RegisterPage = lazy(() => import("./routes/RegisterPage"));
const ChallengesPage = lazy(() => import("./routes/ChallengesPage"));
const ChallengeDetailPage = lazy(() => import("./routes/ChallengeDetailPage"));
const ProfilePage = lazy(() => import("./routes/ProfilePage"));
const LeaderboardPage = lazy(() => import("./routes/LeaderboardPage"));

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-paper flex items-center justify-center">
      <Loader2 size={32} className="text-moss animate-spin" />
    </div>
  );
}

function App() {
  return (
    <OfflineGuard>
      <AuthEvents />
      <Suspense fallback={<LoadingScreen />}>
        <Routes>
        <Route path="/" element={<Navigate to="/challenges" replace />} />

        {/* Public-only auth routes */}
        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <LoginPage />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicOnlyRoute>
              <RegisterPage />
            </PublicOnlyRoute>
          }
        />

        {/* Protected routes */}
        <Route
          path="/challenges"
          element={
            <ProtectedRoute>
              <ChallengesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/challenges/:slug"
          element={
            <ProtectedRoute>
              <ChallengeDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/leaderboard"
          element={
            <ProtectedRoute>
              <LeaderboardPage />
            </ProtectedRoute>
          }
        />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/challenges" replace />} />
        </Routes>
      </Suspense>
    </OfflineGuard>
  );
}

export default App;
