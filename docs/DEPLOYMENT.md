# Deploying ARJUNA AI on Vercel (frontend and backend) with Supabase

Two Vercel projects from the same GitHub repo, plus the Supabase database you already use.

| Project | Root Directory | What it is |
|---|---|---|
| `arjuna-api` | `backend` | FastAPI as a serverless function |
| `arjuna-web` | `frontend` | the React site |

Deploy the **backend first**, because the frontend needs its address.

## 0. Database (Supabase)
- Your `DATABASE_URL` already points at Supabase (the Session pooler, port 5432). Reuse it, or create a second Supabase project for a clean public site and copy its Session pooler string.
- Migrations are **not** run by the host. Run them yourself from your computer against whichever database you chose:
  `cd backend` then `python -m alembic upgrade head` (with that database in `.env`). The shared database is already at the latest version.
- A password with `@ # / %` in it must be percent-encoded inside `DATABASE_URL` (`@` becomes `%40`).

## 1. Backend project (`arjuna-api`)
1. vercel.com > Add New > Project > import this repo > **Root Directory: `backend`**. Vercel reads `backend/vercel.json`, `backend/api/index.py` and `backend/requirements.txt`.
2. Environment variables (Settings > Environment Variables):
   - `DATABASE_URL`: the Supabase Session pooler string
   - `JWT_SECRET`: a long random string (for example 64 characters)
   - `CORS_ORIGINS`: the frontend address you will get in step 2 (add it after step 2, then redeploy). No trailing slash. Several are separated by commas.
   - `GEMINI_API_KEY`, `SARVAM_API_KEY`, and the `SMTP_*` values if you use email
   - `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` if you want interview recording (also create a **private** Storage bucket named `interview-recordings`)
   - Do **not** set `UPLOAD_DIR`; on Vercel it automatically uses `/tmp`.
3. Deploy. Then open `https://<arjuna-api>.vercel.app/health`. It should answer with status ok.

## 2. Frontend project (`arjuna-web`)
1. Add New > Project > same repo > **Root Directory: `frontend`**. The rest comes from `frontend/vercel.json`.
2. Environment variable: `VITE_API_BASE` = `https://<arjuna-api>.vercel.app/api` (ending in `/api`).
3. Deploy. Copy the site address, add it to the backend's `CORS_ORIGINS`, and redeploy the backend.

## 3. Check it
- Open the site, register, upload a resume. The browser console must show no CORS errors (a CORS error means `CORS_ORIGINS` does not match the site address exactly).
- Camera and microphone features need HTTPS, which Vercel provides.

## What is different on Vercel (read this)
- **Time limit.** Each request can run at most `maxDuration` seconds (set to 300 in `backend/vercel.json`). The 100-day plan and the interview report take the longest. If Vercel rejects the number for your plan during deploy, lower it (for example to 60); long AI jobs may then time out on that plan.
- **No saved files.** The original uploaded resume file is not kept after the request. What was read from it (skills, projects, experience) is saved in the database. Interview recordings use Supabase Storage, not disk.
- **Cold starts.** The first request after a quiet period is slower while the function starts.
- **Package size.** To fit Vercel's size limit, scikit-learn, pandas and matplotlib were removed. The text-matching code in `app/modules/textsim.py` gives the same scores as scikit-learn, and the resume fonts are shipped in `app/modules/resume_builder/assets`.
- **Rate limits** are kept in memory, so they apply per function instance, not across all of them.

## Things to watch
- Never commit `.env`. Keys live only in the Vercel dashboard.
- Do not deploy test accounts with weak passwords.
