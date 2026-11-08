# Deploying ARJUNA AI

Frontend on **Vercel**, backend on **Render**, database and file storage on **Supabase**.
Everything below that needs a login is done by you in each dashboard; the repo already holds the config.

## 1. Database (Supabase, which the project already uses)
- Your current `DATABASE_URL` already points at Supabase (the Session pooler, port 5432). That pooler address works from Render as it is: copy the same value into Render.
- Decide whether production should share that database. If it does, the live site shows the same accounts and data as your team's development, including test accounts. For a clean public site, create a second Supabase project, copy its Session pooler string (Project Settings > Database > Connection string > Session pooler), and let the backend create the tables on first start (`alembic upgrade head` runs automatically).
- To bring the existing data across instead: `pg_restore --no-owner --no-acl -d "<connection string>" arjuna_ai_backup.dump`.
- Interview recordings: in the same Supabase project create a **private** Storage bucket named `interview-recordings`, then set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` on Render. Without them recording stays hidden. The service-role key is a secret: it goes only into Render's dashboard, never into the repo or the frontend.

## 2. Backend on Render
1. render.com > New > Blueprint > choose this GitHub repo. It reads `render.yaml`.
2. Fill in the secrets it asks for:
   - `DATABASE_URL`: the Supabase Session pooler string
   - `CORS_ORIGINS`: your Vercel address, e.g. `https://arjuna-ai.vercel.app` (add more with commas; no trailing slash)
   - `GEMINI_API_KEY`, `SARVAM_API_KEY`, and the `SMTP_*` values if you use email
   - `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` if you want interview recording
   - `JWT_SECRET` is generated for you
3. The plan is Starter because the persistent disk (resume uploads) and always-on service need a paid plan. On a free plan, uploads vanish on restart and the first request after idle is slow.
4. When it is live, `https://<service>.onrender.com/health` should answer.

## 3. Frontend on Vercel
1. vercel.com > Add New > Project > import this repo.
2. **Root Directory: `frontend`.** The rest comes from `frontend/vercel.json` (Vite, `npm install --legacy-peer-deps`, output `dist`).
3. Environment variable: `VITE_API_BASE` = `https://<service>.onrender.com/api` (with `/api` at the end).
4. Deploy. Then put the Vercel address into the backend's `CORS_ORIGINS` and redeploy the backend.

The frontend talks to the backend directly, so long AI calls (the 100-day plan can take minutes) are not cut off by a proxy.

## 4. Check it
- Open the Vercel address, register an account, upload a resume.
- Open the browser console: no CORS errors. A CORS error means `CORS_ORIGINS` does not match the site address exactly.
- Camera and microphone features need HTTPS, which both hosts provide.

## Things to watch
- Never commit `.env`. Keys live only in the Render and Vercel dashboards.
- Do not deploy test accounts with weak passwords.
- Interview recordings use Supabase Storage if `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set; otherwise recording is hidden.
- Each teammate's `alembic upgrade head` and the production one share the same migration files; run migrations only through the deploy, not by hand against production.
