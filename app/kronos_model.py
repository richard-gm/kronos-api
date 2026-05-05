"""
Thin wrapper around the Kronos foundation model.

Kronos source is cloned from github.com/shiyu-coder/Kronos during the Docker
build and placed at /app/kronos_src (renamed from 'model' to avoid shadowing
stdlib). PYTHONPATH=/app ensures 'kronos_src' is importable.
"""

import sys
import logging
import pandas as pd
import numpy as np
from datetime import timedelta

logger = logging.getLogger(__name__)

# Kronos is not a PyPI package — it's vendored into the image at build time
sys.path.insert(0, "/app")
from kronos_src import Kronos, KronosTokenizer, KronosPredictor  # noqa: E402


class KronosModel:
    """Singleton — model is loaded once at startup and reused for all requests."""

    _instance: "KronosModel | None" = None

    def __init__(self, model_name: str, tokenizer_name: str) -> None:
        logger.info(f"Loading tokenizer from {tokenizer_name}")
        self.tokenizer = KronosTokenizer.from_pretrained(tokenizer_name)
        logger.info(f"Loading model from {model_name}")
        self.model = Kronos.from_pretrained(model_name)
        self.predictor = KronosPredictor(self.model, self.tokenizer, max_context=512)
        logger.info("Kronos ready")

    @classmethod
    def load(cls, model_name: str, tokenizer_name: str) -> "KronosModel":
        if cls._instance is None:
            cls._instance = cls(model_name, tokenizer_name)
        return cls._instance

    def score(self, ticker: str, df: pd.DataFrame, pred_days: int, sample_count: int = 1) -> dict:
        """
        Run Kronos inference on historical OHLCV and return a directional signal.

        Returns a dict with: ticker, predicted_return (%), signal, confidence,
        last_close, predicted_close, pred_days.
        """
        x_timestamps = df.index.tolist()
        # Use business-day offsets so Kronos sees realistic future dates
        y_timestamps = list(
            pd.bdate_range(start=df.index[-1] + timedelta(days=1), periods=pred_days)
        )

        pred_df = self.predictor.predict(
            df=df,
            x_timestamp=x_timestamps,
            y_timestamp=y_timestamps,
            pred_len=pred_days,
            T=1.0,
            top_p=0.9,
            sample_count=sample_count,
        )

        last_close = float(df["close"].iloc[-1])
        predicted_close = float(pred_df["close"].iloc[-1])
        predicted_return = (predicted_close - last_close) / last_close * 100  # %

        if predicted_return > 2.0:
            signal = "BULLISH"
        elif predicted_return < -2.0:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "ticker": ticker,
            "predicted_return": round(predicted_return, 2),
            "signal": signal,
            "confidence": round(abs(predicted_return), 2),
            "last_close": round(last_close, 2),
            "predicted_close": round(predicted_close, 2),
            "pred_days": pred_days,
        }
