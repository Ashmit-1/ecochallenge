import { Routes, Route, Navigate } from "react-router-dom";

function App() {
  return (
    <Routes>
      {/* Placeholder routes — will be built out in subsequent milestones */}
      <Route path="/" element={<Navigate to="/challenges" replace />} />
      <Route
        path="/challenges"
        element={
          <main className="min-h-screen bg-paper p-5 md:p-8 max-w-[1120px] mx-auto">
            <h1 className="font-display text-3xl font-semibold text-ink mb-4">
              EcoChallenge
            </h1>
            <p className="text-ink-soft font-body">
              Scaffold is live. API client and TanStack Query layer are ready.
            </p>
          </main>
        }
      />
    </Routes>
  );
}

export default App;
