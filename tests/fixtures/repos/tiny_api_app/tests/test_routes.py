from app.routes import route


def test_health_route() -> None:
    assert route("/health") == "ok"


def test_contacts_route() -> None:
    assert route("/v1/contacts") == "[]"
