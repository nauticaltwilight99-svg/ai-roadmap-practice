# Auto-Company backup and restore

The portable source backup is created without live secrets, runtime databases,
or process state. A separate `with-logs` archive may include diagnostic logs.

## Restore

1. Extract the archive into a new directory.
2. Copy `.env.example` to `.env`.
3. Fill in the API keys, Telegram token, dashboard password, and other
   environment values locally. Do not commit `.env`.
4. Install Docker Desktop (Windows) or Docker Engine (Linux).
5. Run:

```powershell
docker compose up -d --build
```

6. Check the dashboard at `http://localhost:8787`.
7. Start the direct Telegram bot and workers through the compose services.

## What is intentionally excluded

- `.env` and all live credentials;
- SQLite/runtime files under `.runtime`;
- PID/state files (the `with-logs` archive retains diagnostic logs);
- Python virtual environments and caches;
- generated output that is not source code.

The archive is the portable source backup. Keep the secret values in a
separate password manager or encrypted secret store.
