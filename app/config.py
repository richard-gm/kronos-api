import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    api_key: str = field(default_factory=lambda: os.environ.get("API_KEY", ""))
    alpaca_api_key: str = field(default_factory=lambda: os.environ.get("ALPACA_API_KEY", ""))
    alpaca_secret_key: str = field(default_factory=lambda: os.environ.get("ALPACA_SECRET_KEY", ""))
    supabase_url: str = field(default_factory=lambda: os.environ.get("SUPABASE_URL", ""))
    supabase_anon_key: str = field(default_factory=lambda: os.environ.get("SUPABASE_ANON_KEY", ""))
    kronos_model: str = field(default_factory=lambda: os.environ.get("KRONOS_MODEL", "NeoQuasar/Kronos-small"))
    kronos_tokenizer: str = field(default_factory=lambda: os.environ.get("KRONOS_TOKENIZER", "NeoQuasar/Kronos-Tokenizer-base"))
    pred_days: int = field(default_factory=lambda: int(os.environ.get("PRED_DAYS", "10")))
    lookback_days: int = field(default_factory=lambda: int(os.environ.get("LOOKBACK_DAYS", "130")))
    cors_origins: List[str] = field(
        default_factory=lambda: os.environ.get(
            "CORS_ORIGINS", "http://localhost:3000"
        ).split(",")
    )
    portfolio_tickers: List[str] = field(
        default_factory=lambda: [
            t.strip()
            for t in os.environ.get("PORTFOLIO_TICKERS", "AAPL,MSFT").split(",")
            if t.strip()
        ]
    )

    def validate(self) -> None:
        missing = [
            name
            for name, val in [
                ("API_KEY", self.api_key),
                ("ALPACA_API_KEY", self.alpaca_api_key),
                ("ALPACA_SECRET_KEY", self.alpaca_secret_key),
                ("SUPABASE_URL", self.supabase_url),
                ("SUPABASE_ANON_KEY", self.supabase_anon_key),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


settings = Settings()
