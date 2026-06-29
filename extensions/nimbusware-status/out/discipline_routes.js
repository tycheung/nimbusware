"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseDisciplineMentions = parseDisciplineMentions;
exports.disciplineRoutes = disciplineRoutes;
const MENTION_RE = /@([a-zA-Z][\w-]*)/g;
const DISCIPLINES = {
    pm: { taxonomy: "planner", aliases: ["product"] },
    architect: { taxonomy: "architect", aliases: ["arch"] },
    frontend: { taxonomy: "frontend_writer", aliases: ["fe", "ui"] },
    backend: { taxonomy: "backend_writer", aliases: ["be", "api"] },
    qa: { taxonomy: "test_writer", aliases: ["test", "quality"] },
    devops: { taxonomy: ["integration_adapter_writer", "infra_writer"], aliases: ["ops", "infra"] },
    fullstack: { taxonomy: ["frontend_writer", "backend_writer"], aliases: ["fs"] },
};
function resolveDiscipline(raw) {
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
function parseDisciplineMentions(message) {
    const out = [];
    const seen = new Set();
    for (const match of message.matchAll(MENTION_RE)) {
        const discipline = resolveDiscipline(match[1]);
        if (discipline && !seen.has(discipline)) {
            seen.add(discipline);
            out.push(discipline);
        }
    }
    return out;
}
function disciplineRoutes(message, soloHat) {
    const mentions = parseDisciplineMentions(message);
    if (mentions.length) {
        const routes = [];
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
//# sourceMappingURL=discipline_routes.js.map