# Adding `searchos_db` to your existing stack

I can't reach your server from this sandbox, so this is the one manual edit
you need to make yourself — everything else (the searchos-api service,
config, code) is already wired to expect this database to exist.

## Edit `postgres-init` in your main `docker-compose.yml`

Find this block:

```yaml
    command: >
      sh -c "
        psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'CREATE DATABASE n8n_db;'            2>/dev/null || true &&
        psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'CREATE DATABASE postiz_db;'         2>/dev/null || true &&
        psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'CREATE DATABASE freight_users_db;'  2>/dev/null || true &&
        echo 'All databases ready.'
      "
```

Add one more line before `echo 'All databases ready.'`:

```yaml
    command: >
      sh -c "
        psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'CREATE DATABASE n8n_db;'            2>/dev/null || true &&
        psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'CREATE DATABASE postiz_db;'         2>/dev/null || true &&
        psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'CREATE DATABASE freight_users_db;'  2>/dev/null || true &&
        psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'CREATE DATABASE searchos_db;'       2>/dev/null || true &&
        echo 'All databases ready.'
      "
```

Then re-run just that one-shot container (it already has `restart: "no"`,
so it exits after running once):

```bash
docker compose up postgres-init
```

## Add one variable to your real `.env`

This repo's `.env.example` documents everything search-os needs, but the
one thing not already in your `.env` is a JWT signing secret scoped to
search-os (deliberately separate from `N8N_ENCRYPTION_KEY` — different
services should not share a signing secret):

```bash
SEARCHOS_JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
```

## Then bring it up

```bash
cd ~/SureShiftERP
docker compose -f docker-compose.yml -f sureshift-search-os/infra/docker-compose.searchos.yml \
  --env-file .env up -d --build searchos-api

curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "service": "search-growth-os-api", "phase": "0", "environment": "production"}
```
