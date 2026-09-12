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

## Reusing the existing password

Per your instruction, `JWT_SECRET_KEY` is wired to reuse `${POSTGRES_PASSWORD}`
from your existing `.env` (`RaViGo1140`) rather than a separate secret — no
new variable needed for this step. Flagged once: this is a different kind of
risk than reusing it for Postgres/Redis, since a JWT secret leak lets someone
forge valid auth tokens for the API rather than just access data. Worth
rotating this one specifically to something unique when you do your cleanup,
even before the others.

## Then bring it up

No new `.env` variables needed — just the `searchos_db` step above.

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
