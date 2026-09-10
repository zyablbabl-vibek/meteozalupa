from app.config.settings import Settings


def test_cors_origins_are_parsed_and_normalized() -> None:
    configured = Settings(
        cors_origins=" https://weather.example.com/, https://preview.example.com "
    )

    assert configured.allowed_cors_origins == [
        "https://weather.example.com",
        "https://preview.example.com",
    ]


def test_empty_cors_entries_are_ignored() -> None:
    configured = Settings(cors_origins="https://weather.example.com,, ")

    assert configured.allowed_cors_origins == ["https://weather.example.com"]
