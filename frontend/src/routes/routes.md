# routes/

One file per page/screen.

| File | Purpose |
|---|---|
| [LoginPage.tsx](LoginPage.tsx) | Email/password sign-in, redirects to `from` or `/challenges` |
| [RegisterPage.tsx](RegisterPage.tsx) | Account creation with validation, auto-login on success |
| [ChallengesPage.tsx](ChallengesPage.tsx) | Challenge catalogue with icons, points, CO₂, cooldown chips |
| [ChallengeDetailPage.tsx](ChallengeDetailPage.tsx) | Full challenge info + photo submission flow with AI verification states |
| [ProfilePage.tsx](ProfilePage.tsx) | Stats grid, editable display name, badge progress bars, CO₂ estimate |
| [LeaderboardPage.tsx](LeaderboardPage.tsx) | Tabular ranks, current-user highlight, tie semantics preserved |
