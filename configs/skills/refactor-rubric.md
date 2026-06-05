# Refactor rubric

- Prefer edits that shrink diff surface area.
- Do not rename public APIs without an explicit slice goal.
- Keep imports acyclic; extract helpers instead of growing god modules.
- Run scoped pytest before claiming refactor complete.
