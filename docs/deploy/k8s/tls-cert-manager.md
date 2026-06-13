# TLS with cert-manager (Helm)

Use cert-manager to issue TLS certificates for the Nimbusware API Ingress when running on Kubernetes.

## Prerequisites

- cert-manager installed in the cluster ([installation docs](https://cert-manager.io/docs/installation/))
- Helm chart with `ingress.enabled=true` and `ingress.tls=true`
- DNS for `ingress.host` pointing at the Ingress load balancer

## Enable chart templates

```bash
helm upgrade nimbusware charts/nimbusware \
  --set ingress.enabled=true \
  --set ingress.host=api.example.com \
  --set ingress.className=nginx \
  --set ingress.tls=true \
  --set ingress.tlsSecretName=nimbusware-api-tls \
  --set hardening.certManager.enabled=true \
  --set hardening.certManager.clusterIssuer=true \
  --set hardening.certManager.email=ops@example.com
```

When `hardening.certManager.enabled` is true, the chart renders a `Certificate` that writes the TLS secret referenced by Ingress (`ingress.tlsSecretName`).

When `hardening.certManager.clusterIssuer` is true, a stub `ClusterIssuer` (Let's Encrypt HTTP-01) is included. Production clusters often prefer a pre-provisioned issuer — set `clusterIssuer=false` and create the issuer separately, then match `hardening.certManager.issuerName`.

## Multi-AZ pod spread

Spread API pods across availability zones when running multiple replicas:

```bash
helm upgrade nimbusware charts/nimbusware \
  --set api.replicas=3 \
  --set hardening.multiAz.enabled=true
```

This adds preferred `podAntiAffinity` on `topology.kubernetes.io/zone` to `api-deployment.yaml`.

## Verify

```bash
kubectl get certificate -n <namespace>
kubectl describe ingress nimbusware-api
curl -I https://api.example.com/v1/platform/edition
```

See also: [helm.md](../helm.md), [k8s/README.md](README.md).
