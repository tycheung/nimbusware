# Helm install (production-oriented reference)

Chart path: [`charts/nimbusware`](../../charts/nimbusware).

## Prerequisites

- Kubernetes 1.28+
- Helm 3.12+
- Container image built from this repo (`nimbusware-api:latest` by default)
- Managed Postgres recommended for production (`labPostgres.enabled=false`)

## Install

```bash
helm install nimbusware charts/nimbusware \
  --set secrets.databaseUrl='postgresql://USER:PASS@host:5432/nimbusware' \
  --set secrets.adminToken='your-rotated-admin-token' \
  --set edition=enterprise
```

Lab stack with in-cluster Postgres (non-production):

```bash
helm install nimbusware-lab charts/nimbusware \
  --set labPostgres.enabled=true \
  --set secrets.databaseUrl='postgresql://nimbusware:nimbusware@postgres:5432/nimbusware'
```

## Upgrade and rollback

```bash
helm upgrade nimbusware charts/nimbusware -f my-values.yaml
helm rollback nimbusware 1
```

## Ingress and TLS

```bash
helm upgrade nimbusware charts/nimbusware \
  --set ingress.enabled=true \
  --set ingress.host=api.example.com \
  --set ingress.className=nginx \
  --set ingress.tls=true \
  --set ingress.tlsSecretName=nimbusware-api-tls
```

Create TLS secret `nimbusware-api-tls` in the release namespace before enabling TLS, or use cert-manager:

```bash
helm upgrade nimbusware charts/nimbusware \
  --set ingress.enabled=true \
  --set ingress.host=api.example.com \
  --set ingress.className=nginx \
  --set ingress.tls=true \
  --set ingress.annotations."cert-manager\.io/cluster-issuer"=letsencrypt-prod
```

Pod templates include `checksum/secrets` annotations so `helm upgrade` rolls API and worker pods when secret values change.

## Secrets rotation

Update `secrets.databaseUrl` / `secrets.adminToken` in values, run `helm upgrade`, then restart API and worker pods.

Raw YAML reference manifests remain in [`k8s/`](k8s/) for `kubectl apply --dry-run=client` smoke checks.
