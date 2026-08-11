from app.logging_config import scrub_event


def test_scrub_event_redacts_nested_strings_and_lists() -> None:
    event = {
        "event": "request_received",
        "payload": {
            "message": "Contact student@vinuni.edu.vn or 090 123 4567",
            "nested": {"passport": "B12345678"},
        },
        "notes": ["Card 4111 1111 1111 1111"],
    }

    redacted = scrub_event(None, "info", event)

    rendered = str(redacted)
    assert "student@vinuni.edu.vn" not in rendered
    assert "090 123 4567" not in rendered
    assert "B12345678" not in rendered
    assert "4111 1111 1111 1111" not in rendered
    assert "[REDACTED_EMAIL]" in rendered
    assert "[REDACTED_PHONE_VN]" in rendered
    assert "[REDACTED_PASSPORT]" in rendered
    assert "[REDACTED_CREDIT_CARD]" in rendered
