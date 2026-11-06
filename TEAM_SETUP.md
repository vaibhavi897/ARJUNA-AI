# Team development setup

Interview history is stored in PostgreSQL and is private to the signed-in account. Each developer's backend must connect to the same PostgreSQL database to see the same account's sessions. A successful login against a separate local database can still show an empty history.

## Configure each developer's backend

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `DATABASE_URL` to the team's shared PostgreSQL connection string and `JWT_SECRET` to the same team secret on every backend. Share these values through a password manager or another secret store; do not commit them or send them in chat.
3. From `backend/`, install dependencies and apply migrations:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m alembic upgrade head
   ```

4. Start the backend on port 8000. The Vite dev server forwards `/api` to `http://127.0.0.1:8000` by default, so each developer can run a local backend while all backends use the shared database.

Make sure each person signs into the same account when they need to see that account's interview history. Sessions remain isolated between different accounts by design.

## Verify the connection

Open `http://127.0.0.1:8000/health` on each developer's machine. It should report `status: "ok"` and `database.connected: true`. Then sign in with the same account and refresh Interview Arena history.

The frontend's Vite proxy target can be changed with `API_TARGET` if the team uses a shared backend server instead of local backends. Never point development builds at production data without the team's approval.
