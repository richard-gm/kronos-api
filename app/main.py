import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth import validate_api_key
from app.config import settings
from app.data import fetch_ohlcv
from app.kronos_model import KronosModel
from app.storage import write_scores

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    KronosModel.load(settings.kronos_model, settings.kronos_tokenizer)
    yield


app = FastAPI(title="Kronos API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Api-Key", "Content-Type"],
)


class StockRequest(BaseModel):
    ticker: str
    pred_days: int = 10
    # Use sample_count > 1 for ensemble averaging (slower, more stable)
    sample_count: int = 1


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": settings.kronos_model}


@app.post("/score/stock", dependencies=[Depends(validate_api_key)])
async def score_stock(req: StockRequest):
    """Score a single ticker on demand. Writes result to Supabase."""
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


@app.post("/score/portfolio", dependencies=[Depends(validate_api_key)])
async def score_portfolio():
    """Score all portfolio tickers. Writes all results to Supabase."""
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
            logger.error(f"{ticker}: {e}")
            errors.append({"ticker": ticker, "error": str(e)})

    if results:
        await write_scores(results, settings.supabase_url, settings.supabase_anon_key)

    return {"scored": len(results), "errors": errors, "results": results}
