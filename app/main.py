"""
Kronos API — FastAPI application entry point.

Route summary:
  GET  /health              — liveness check (no auth)
  POST /score/stock         — synchronous single-ticker inference (~10 s on M4 CPU)
  POST /score/portfolio     — async portfolio inference; returns 202 immediately,
                              runs inference in a BackgroundTask, writes to Supabase
                              when complete. Required because the full portfolio run
                              takes several minutes — longer than Vercel's 10 s timeout.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth import validate_api_key
from app.config import settings
from app.data import fetch_ohlcv
from app.kronos_model import KronosModel
from app.storage import write_scores

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Startup ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan hook — runs once on startup, once on shutdown.
    Pre-loading the model here means the first request doesn't pay the
    ~10-second model load penalty.
    """
    settings.validate()
    await asyncio.to_thread(KronosModel.load, settings.kronos_model, settings.kronos_tokenizer)
    yield  # app serves requests between yield and shutdown


app = FastAPI(title="Kronos API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Api-Key", "Content-Type"],
)

# ── Request models ────────────────────────────────────────────────────────────


class StockRequest(BaseModel):
    ticker: str
    pred_days: int = 10
    # sample_count > 1 averages multiple Kronos samples (ensemble) for
    # more stable predictions at the cost of proportionally more compute time.
    sample_count: int = 1


# ── Background task ───────────────────────────────────────────────────────────


async def _run_portfolio_background() -> None:
    """
    Scores all PORTFOLIO_TICKERS and writes results to Supabase.

    This is intentionally an async function (not a sync one) so that FastAPI
    runs it in the same event loop rather than a thread pool — important because
    the Kronos model is not thread-safe.

    Called via FastAPI's BackgroundTasks so the HTTP response (202 Accepted)
    is sent to the caller *before* this function starts, decoupling the
    client's timeout from the inference duration.
    """
    model = KronosModel.load(settings.kronos_model, settings.kronos_tokenizer)
    results, errors = [], []

    for ticker in settings.portfolio_tickers:
        try:
            df = await fetch_ohlcv(
                ticker, settings.lookback_days,
                settings.alpaca_api_key, settings.alpaca_secret_key,
            )
            result = model.score(ticker, df, settings.pred_days, sample_count=1)
            results.append(result)
            logger.info(f"{ticker}: {result['signal']} ({result['predicted_return']:+.2f}%)")
        except Exception as e:
            logger.error(f"{ticker} failed: {e}")
            errors.append({"ticker": ticker, "error": str(e)})

    if results:
        await write_scores(results, settings.supabase_url, settings.supabase_anon_key)
        logger.info(f"Portfolio run complete: {len(results)} scored, {len(errors)} errors")


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Liveness check — no authentication required."""
    return {"status": "ok", "model": settings.kronos_model}


@app.post("/score/stock", dependencies=[Depends(validate_api_key)])
async def score_stock(req: StockRequest):
    """
    Score a single ticker synchronously.

    Returns the Kronos signal directly in the response body and writes it to
    Supabase. Single-ticker inference takes ~10 s on M4 CPU — fast enough
    to fit within Vercel's serverless function timeout.
    """
    try:
        df = await fetch_ohlcv(
            req.ticker, settings.lookback_days,
            settings.alpaca_api_key, settings.alpaca_secret_key,
        )
        result = KronosModel.load(settings.kronos_model, settings.kronos_tokenizer).score(
            req.ticker, df, req.pred_days, req.sample_count
        )
        await write_scores([result], settings.supabase_url, settings.supabase_anon_key)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error scoring {req.ticker}: {e}")
        raise HTTPException(status_code=500, detail="Inference failed — check server logs")


@app.post("/score/portfolio", status_code=202, dependencies=[Depends(validate_api_key)])
async def score_portfolio(background_tasks: BackgroundTasks):
    """
    Trigger a full portfolio scoring run asynchronously.

    Returns 202 Accepted immediately — the actual inference runs in the
    background after this response is sent. Results are written to Supabase
    when the run completes; the frontend should refresh the page to pick them up.

    This async design is required because:
    - Portfolio inference takes several minutes on CPU.
    - Vercel's free tier terminates functions after 10 seconds.
    - The client should not be blocked waiting for the result.
    """
    background_tasks.add_task(_run_portfolio_background)
    return {
        "status": "queued",
        "tickers": settings.portfolio_tickers,
        "message": "Inference running in background. Refresh in a few minutes.",
    }
