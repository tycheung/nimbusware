# nimbusware_maker_web

Static Maker web PWA served at `/v1/maker/app/`.

## Features

- Run theater and research brief approve/reject
- Slice progress (`GET /v1/runs/{id}/maker-progress`)
- Slice approval (`GET /v1/runs/{id}/maker/pending`, plan approve, slice apply/skip, prepare)

## Files

- `static/index.html`, `app.js`, `styles.css`, `manifest.json`

Mount: [`packages/nimbusware_api/routes/maker_web.py`](../nimbusware_api/routes/maker_web.py).
