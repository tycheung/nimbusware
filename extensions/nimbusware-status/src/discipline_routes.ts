const MENTION_RE = /@([a-zA-Z][\w-]*)/g;

const DISCIPLINES: Record<string, { taxonomy: string | string[]; aliases: string[] }> = {
  pm: { taxonomy: "planner", aliases: ["product"] },
  architect: { taxonomy: "architect", aliases: ["arch"] },
  frontend: { taxonomy: "frontend_writer", aliases: ["fe", "ui"] },
  backend: { taxonomy: "backend_writer", aliases: ["be", "api"] },
  qa: { taxonomy: "test_writer", aliases: ["test", "quality"] },
  devops: { taxonomy: ["integration_adapter_writer", "infra_writer"], aliases: ["ops", "infra"] },
  fullstack: { taxonomy: ["frontend_writer", "backend_writer"], aliases: ["fs"] },
};

export interface DisciplineRoute {
  discipline: string;
  taxonomy_key: string;
  source: "mention" | "solo_hat";
}

function resolveDiscipline(raw: string): string | null {
  const key = raw.toLowerCase().replace(/^@/, "");
  if (DISCIPLINES[key]) {
    return key;
  }
  for (const [id, row] of Object.entries(DISCIPLINES)) {
    if (row.aliases.includes(key)) {
      return id;
    }
  }
  return null;
}

export function parseDisciplineMentions(message: string): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const match of message.matchAll(MENTION_RE)) {
    const discipline = resolveDiscipline(match[1]);
    if (discipline && !seen.has(discipline)) {
      seen.add(discipline);
      out.push(discipline);
    }
  }
  return out;
}

export function disciplineRoutes(message: string, soloHat?: string): DisciplineRoute[] {
  const mentions = parseDisciplineMentions(message);
  if (mentions.length) {
    const routes: DisciplineRoute[] = [];
    for (const discipline of mentions) {
      const tax = DISCIPLINES[discipline].taxonomy;
      const keys = Array.isArray(tax) ? tax : [tax];
      for (const taxonomy_key of keys) {
        routes.push({ discipline, taxonomy_key, source: "mention" });
      }
    }
    return routes;
  }
  const hat = String(soloHat || "").trim().toLowerCase();
  if (hat && DISCIPLINES[hat]) {
    const tax = DISCIPLINES[hat].taxonomy;
    const keys = Array.isArray(tax) ? tax : [tax];
    return keys.map((taxonomy_key) => ({ discipline: hat, taxonomy_key, source: "solo_hat" }));
  }
  return [];
}
