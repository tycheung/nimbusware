from __future__ import annotations

from orchestrator.interaction_surface_map import discover_interactive_surfaces_from_html


def test_discover_buttons_and_inputs() -> None:
    html = """
    <html><body>
      <button>Add todo</button>
      <input data-testid="todo-title-input" />
      <form></form>
    </body></html>
    """
    surfaces = discover_interactive_surfaces_from_html(html)
    kinds = {s.kind for s in surfaces}
    assert "button" in kinds
    assert "input" in kinds
    assert "form" in kinds
