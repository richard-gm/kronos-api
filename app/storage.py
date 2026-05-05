from supabase import create_client, Client
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client(url: str, key: str) -> Client:
    global _client
    if _client is None:
        _client = create_client(url, key)
    return _client


async def write_scores(scores: list[dict], url: str, key: str) -> None:
    if not scores:
        return
    client = get_client(url, key)
    run_at = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "ticker": s["ticker"],
            "predicted_return": s["predicted_return"],
            "signal": s["signal"],
            "confidence": s["confidence"],
            "last_close": s["last_close"],
            "predicted_close": s["predicted_close"],
            "pred_days": s["pred_days"],
            "run_at": run_at,
        }
        for s in scores
    ]
    # Upsert on ticker — one row per ticker, always the latest score
    client.table("kronos_scores").upsert(rows, on_conflict="ticker").execute()
    logger.info(f"Wrote {len(rows)} scores to Supabase")
