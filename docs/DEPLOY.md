# Deploying

This is a single stateless container. No database, no Redis, no volume, no
worker, no cron. That is the whole reason it is cheap to run.

---

## Railway

### 1. Push the repo, then point Railway at it

```bash
npm i -g @railway/cli   # or: brew install railway
railway login
railway init
railway up
```

Or connect the GitHub repo from the Railway dashboard — **New Project → Deploy
from GitHub repo** — which gives you a deploy on every push.

### 2. There is nothing to configure

Railway reads [`railway.toml`](../railway.toml) at the repo root:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
numReplicas = 1
```

It builds the [`Dockerfile`](../Dockerfile) and waits for `/health` to answer
before routing traffic to the new deploy. `/health` makes no upstream calls, so
it responds instantly even on a cold container.

### 3. Give it a domain

```bash
railway domain
```

That prints a `*.up.railway.app` URL. Open it and the portal is there; add
`/docs` for the API reference.

### The one thing that has to be right: `$PORT`

Railway assigns your container a port at runtime and injects it as `PORT`. If
the app listens anywhere else, the healthcheck never passes and the deploy hangs
and then fails — this is the single most common Python-on-Railway problem.

The Dockerfile handles it:

```dockerfile
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
```

Three details matter here:

- **Shell form, not exec form.** `CMD ["uvicorn", …, "--port", "$PORT"]` passes
  the literal string `$PORT` to uvicorn. Only a shell expands it.
- **`--host 0.0.0.0`**, never `127.0.0.1` — otherwise nothing outside the
  container can reach it.
- **`--proxy-headers`**, because Railway terminates TLS in front of you. Without
  it the app thinks every request arrived over plain HTTP from the proxy's IP.

`${PORT:-8000}` keeps `docker run -p 8000:8000` working locally.

### Environment variables

Set these under **Variables** in the service. All are optional.

| Variable | Why |
| --- | --- |
| `CVBIO_USER_AGENT` | GBIF and Wikipedia ask for a contactable User-Agent. Point it at your repo. |
| `CVBIO_CORS_ORIGINS` | Restrict the portal's origins once you have a real domain. Accepts `a.example,b.example` or a JSON array. |
| `CVBIO_PROTECTED_PLANET_TOKEN` | Swap the bundled INGT protected-areas data for live WDPA records. |
| `CVBIO_CACHE_TTL` | Seconds to cache upstream responses (default 900). Raise it to cut outbound traffic. |

**Do not set `PORT` yourself.** Railway injects it.

### Cost and scaling

Railway bills for what the container actually uses. This app is idle most of the
time — it holds no connections, runs no background work, and answers cached
requests in single-digit milliseconds — so it sits near the bottom of the usage
curve.

The cache is **per replica**, held in that process's memory. Raising
`numReplicas` buys availability, at the cost of each replica warming its own
cache and each making its own upstream calls. Start at 1. If you need to serve
real traffic, put a CDN in front before you add replicas — most responses are
public and identical for every caller.

### Deploying without Docker

If you would rather Railway build the Python app itself, delete or ignore the
Dockerfile and set:

```toml
[build]
builder = "RAILPACK"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers"
healthcheckPath = "/health"
```

Railway reads [`.python-version`](../.python-version) for the interpreter (3.11)
and installs from `uv.lock`. The Dockerfile path is still recommended: the build
is identical everywhere, so what you test locally is what ships.

---

## Other hosts

The same container runs anywhere. All of these inject `$PORT` the same way, so
no changes are needed.

**Fly.io**

```bash
fly launch --no-deploy      # generates fly.toml from the Dockerfile
fly deploy
```

Set `internal_port = 8000` in `fly.toml`, or leave `$PORT` to it.

**Render** — New → Web Service → Docker. Health check path `/health`.

**Google Cloud Run**

```bash
gcloud run deploy cabo-verde-biodiversity --source . --allow-unauthenticated
```

Cloud Run scales to zero, which suits this app well: a cold start is one Python
process, and the first request after a scale-up simply refills the cache.

**Plain Docker**

```bash
docker build -t cabo-verde-biodiversity .
docker run -p 8000:8000 cabo-verde-biodiversity
```

---

## Health and troubleshooting

`GET /health` returns liveness plus live cache statistics:

```json
{ "status": "ok", "version": "0.1.0",
  "cache": { "hits": 40, "misses": 26, "hit_rate": 0.606, "entries": 26 } }
```

A low `hit_rate` under steady traffic means the TTL is short for your usage —
raise `CVBIO_CACHE_TTL`.

| Symptom | Cause |
| --- | --- |
| Deploy hangs, then healthcheck fails | The app is not listening on `$PORT`. Check the start command. |
| Container starts then exits immediately | Usually a bad `CVBIO_*` value. The logs name the field. |
| `502` / `504` from an endpoint | An upstream is down. `/health`, `/v1/islands` and `/v1/protected-areas` need no upstream and stay up. |
| Portal loads but panels say "Could not load" | `CVBIO_CORS_ORIGINS` does not include the domain you are browsing from. |
