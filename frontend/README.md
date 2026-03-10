# Runlens frontend

Next.js 14 (App Router), TypeScript, Tailwind CSS. Consumes the Runlens FastAPI backend for gait analysis.

Local dev: from repo root see main README; from here run `npm install` and `npm run dev` (ensure backend is running and `NEXT_PUBLIC_API_URL` is set in `.env.local` if needed).

---

### Deploying to Vercel

1. Push latest changes to GitHub main branch
2. Go to vercel.com → New Project → Import your GitHub repo
3. Set Root Directory to: **frontend**
4. Framework preset: Next.js (auto-detected)
5. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://gait-analyzer-hc0p.onrender.com/`
6. Click Deploy
7. After deploy, copy your Vercel URL (e.g. `https://runlens.vercel.app`)
8. Add that URL to CORS allowed origins in `backend/main.py` on Render
9. Redeploy backend on Render for CORS change to take effect

### Custom Domain (optional)

- In Vercel dashboard → Settings → Domains → Add runlens.io
- Add the DNS records Vercel provides to your domain registrar
- Vercel handles SSL automatically

### Ongoing Deploys

- Every push to main branch auto-deploys to Vercel
- Preview deployments are created automatically for every PR
