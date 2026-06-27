from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HeuristicSliceSpec:
    slice_id: str
    title: str
    rationale: str
    target_suffixes: tuple[str, ...] = ()
    estimated_loc: int = 80
    surface_id: str | None = None
    stack_id: str | None = None


@dataclass(frozen=True)
class HeuristicTemplate:
    template_id: str
    feature_title: str
    acceptance: tuple[str, ...]
    slices: tuple[HeuristicSliceSpec, ...]


KEYWORD_TEMPLATES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("crm", "customer", "contact", "sales"), "crm"),
    (("todo", "task list", "tasks"), "todo_api"),
    (("contact", "rest api", "health check"), "contacts_api"),
    (("static", "marketing", "landing", "homepage"), "static_site"),
    (("auth", "login", "sign in", "oauth"), "auth_app"),
    (("dashboard", "admin panel", "analytics"), "dashboard"),
)

HEURISTIC_TEMPLATES: dict[str, HeuristicTemplate] = {
    "crm": HeuristicTemplate(
        template_id="crm",
        feature_title="CRM core",
        acceptance=(
            "Health and OpenAPI endpoints respond",
            "Contacts can be listed and created",
            "Auth scaffold present",
        ),
        slices=(
            HeuristicSliceSpec(
                "slice-001",
                "Scaffold",
                "Project scaffold, health route, and OpenAPI shell",
                ("app.py", "main.py", "pyproject.toml"),
                100,
            ),
            HeuristicSliceSpec(
                "slice-002",
                "Auth",
                "User authentication module and session/token stubs",
                ("auth", "users", "login"),
                120,
            ),
            HeuristicSliceSpec(
                "slice-003",
                "Contacts list",
                "Contact model and list endpoint",
                ("contact", "crm", "models"),
                100,
            ),
            HeuristicSliceSpec(
                "slice-004",
                "Contacts create",
                "Create contact endpoint and validation",
                ("contact", "api", "routes"),
                90,
            ),
            HeuristicSliceSpec(
                "slice-005",
                "Tests",
                "API tests for health, auth, and contacts",
                ("test_", "tests/"),
                80,
            ),
        ),
    ),
    "todo_api": HeuristicTemplate(
        template_id="todo_api",
        feature_title="Todo REST API",
        acceptance=("CRUD todo endpoints", "Project tests pass"),
        slices=(
            HeuristicSliceSpec(
                "slice-001", "Scaffold", "App scaffold with health check", ("app.py", "main.py"), 80
            ),
            HeuristicSliceSpec(
                "slice-002",
                "Todo CRUD",
                "Create, list, and delete todo endpoints",
                ("todo", "api", "routes"),
                120,
            ),
            HeuristicSliceSpec(
                "slice-003", "Tests", "REST tests for todo endpoints", ("test_", "tests/"), 70
            ),
        ),
    ),
    "contacts_api": HeuristicTemplate(
        template_id="contacts_api",
        feature_title="Contacts API",
        acceptance=("Health and contacts endpoints", "OpenAPI published"),
        slices=(
            HeuristicSliceSpec(
                "slice-001",
                "Scaffold",
                "FastAPI/Flask scaffold with /health",
                ("app.py", "main.py"),
                70,
            ),
            HeuristicSliceSpec(
                "slice-002",
                "Contacts",
                "List and create contacts endpoints",
                ("contact", "routes"),
                100,
            ),
            HeuristicSliceSpec(
                "slice-003", "Tests", "Integration tests for contacts API", ("test_",), 60
            ),
        ),
    ),
    "static_site": HeuristicTemplate(
        template_id="static_site",
        feature_title="Marketing site",
        acceptance=("Index page loads", "README documents run instructions"),
        slices=(
            HeuristicSliceSpec(
                "slice-001",
                "HTML shell",
                "index.html with layout and primary content",
                ("index.html", "src/", "public/"),
                60,
            ),
            HeuristicSliceSpec(
                "slice-002", "Styles", "CSS theme and responsive layout", (".css", "styles/"), 50
            ),
            HeuristicSliceSpec(
                "slice-003", "Docs", "README and asset polish", ("README", "readme"), 30
            ),
        ),
    ),
    "auth_app": HeuristicTemplate(
        template_id="auth_app",
        feature_title="Authentication",
        acceptance=("Login/register flows", "Protected routes"),
        slices=(
            HeuristicSliceSpec(
                "slice-001",
                "Auth scaffold",
                "User model and password hashing utilities",
                ("auth", "user", "models"),
                100,
            ),
            HeuristicSliceSpec(
                "slice-002",
                "Login API",
                "Login and session/token endpoints",
                ("login", "auth", "routes"),
                90,
            ),
            HeuristicSliceSpec("slice-003", "Tests", "Auth flow tests", ("test_",), 70),
        ),
    ),
    "dashboard": HeuristicTemplate(
        template_id="dashboard",
        feature_title="Dashboard UI",
        acceptance=("Dashboard route renders", "Core widgets wired"),
        slices=(
            HeuristicSliceSpec(
                "slice-001",
                "Layout",
                "Dashboard shell and navigation",
                ("dashboard", "layout", "App."),
                90,
            ),
            HeuristicSliceSpec(
                "slice-002",
                "Widgets",
                "Summary cards and data tables",
                ("components/", "widgets"),
                110,
            ),
            HeuristicSliceSpec(
                "slice-003", "Tests", "UI smoke and component tests", ("test_", ".spec."), 70
            ),
        ),
    ),
    "fullstack_todo": HeuristicTemplate(
        template_id="fullstack_todo",
        feature_title="Full-stack todo app",
        acceptance=(
            "REST API with todo CRUD",
            "Web UI lists and mutates todos against the API",
            "Contract between API and UI is stable",
        ),
        slices=(
            HeuristicSliceSpec(
                "slice-api-001",
                "API scaffold",
                "Backend scaffold with health check",
                ("backend/", "app.py", "main.py", "pyproject.toml"),
                90,
                surface_id="api",
                stack_id="fastapi_python",
            ),
            HeuristicSliceSpec(
                "slice-api-002",
                "Todo CRUD API",
                "Create, list, update, delete todo endpoints",
                ("backend/", "todo", "routes", "api"),
                120,
                surface_id="api",
                stack_id="fastapi_python",
            ),
            HeuristicSliceSpec(
                "slice-api-003",
                "API tests",
                "Backend tests for todo endpoints",
                ("backend/tests", "test_"),
                80,
                surface_id="api",
                stack_id="fastapi_python",
            ),
            HeuristicSliceSpec(
                "slice-web-001",
                "Web scaffold",
                "Frontend shell with routing and API client",
                ("frontend/", "src/", "package.json", "vite.config"),
                100,
                surface_id="web",
                stack_id="react_vite",
            ),
            HeuristicSliceSpec(
                "slice-web-002",
                "Todo UI",
                "List, add, and delete todos in the web UI",
                ("frontend/src", "components", "pages"),
                130,
                surface_id="web",
                stack_id="react_vite",
            ),
            HeuristicSliceSpec(
                "slice-web-003",
                "UI tests",
                "Frontend component or e2e smoke tests",
                ("frontend/", "test_", ".spec."),
                70,
                surface_id="web",
                stack_id="react_vite",
            ),
            HeuristicSliceSpec(
                "slice-contract-001",
                "API/UI contract",
                "Shared OpenAPI or types gate between API and UI",
                ("openapi", "schema", "types"),
                60,
                surface_id="contract",
                stack_id=None,
            ),
        ),
    ),
    "generic": HeuristicTemplate(
        template_id="generic",
        feature_title="Delivery slices",
        acceptance=("Core requirement implemented", "Tests and gates pass"),
        slices=(
            HeuristicSliceSpec(
                "slice-001",
                "Scaffold",
                "Project scaffold aligned to requirements",
                ("app.py", "main.py", "src/", "packages/"),
                80,
            ),
            HeuristicSliceSpec(
                "slice-002", "Core feature", "Primary feature from business prompt", (), 100
            ),
            HeuristicSliceSpec(
                "slice-003",
                "Verification",
                "Tests and gate fixes for implemented feature",
                ("test_", "tests/"),
                70,
            ),
            HeuristicSliceSpec(
                "slice-004",
                "Polish",
                "Docs, error handling, and integration polish",
                ("README", "docs/"),
                50,
            ),
        ),
    ),
}


def match_template_id(prompt: str) -> str:
    lower = prompt.lower()
    if not lower:
        return "generic"
    for keywords, template_id in KEYWORD_TEMPLATES:
        if any(kw in lower for kw in keywords):
            return template_id
    return "generic"
