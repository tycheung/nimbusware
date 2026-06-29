# Archetype journey docs

One **first full-stack app** walkthrough per Maker persona. Each path uses the same core flow — scope discovery in Chat, manifest approval, `campaign_fullstack` delivery, Plan surface badges, Progress deploy cockpit — with persona-specific gates and settings.

| Persona | Archetype id | Setup bundle | Walkthrough |
|---------|--------------|--------------|-------------|
| **Safe Coding** | `safe_coding` | `default` | [safe-coding-first-app.md](safe-coding-first-app.md) |
| **Engineer workspace** | `engineer` | `default` | [engineer-first-app.md](engineer-first-app.md) |
| **Enterprise AI** | `enterprise` | `enterprise` | [enterprise-first-app.md](enterprise-first-app.md) |

**Automated coverage:** mocked Playwright journeys in `tests/e2e/web/maker_archetype_product_journey.spec.ts` (fo2163 + fo2172 + fo2275).

**Related:** [maker.md](../maker.md), [getting-started.md](../../getting-started.md), [install-profiles.md](../../install-profiles.md).
