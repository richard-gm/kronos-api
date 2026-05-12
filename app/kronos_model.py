"""
Thin wrapper around the Kronos foundation model.

Kronos source is cloned from github.com/shiyu-coder/Kronos during the Docker
build and placed at /app/kronos_src (renamed from 'model' to avoid shadowing
stdlib). PYTHONPATH=/app ensures 'kronos_src' is importable.
"""

import sys
import os

os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"

import httpx
from huggingface_hub.utils._http import set_client_factory

def _insecure_client_factory():
    return httpx.Client(verify=False)

set_client_factory(_insecure_client_factory)

import logging
import pandas as pd
import numpy as np
from datetime import timedelta

logger = logging.getLogger(__name__)

sys.path.insert(0, "/app")
from model import Kronos, KronosTokenizer, KronosPredictor

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
        # Use business-day offsets so Kronos sees realistic future dates
        y_timestamps = pd.bdate_range(
            start=df.index[-1] + timedelta(days=1), periods=pred_days
        )

        pred_df = self.predictor.predict(
            df=df,
            x_timestamp=df.index.to_series(),
            y_timestamp=y_timestamps.to_series(),
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

        # Volume spike: compare Kronos-predicted volume to 20-day historical average
        avg_volume = float(df["volume"].tail(20).mean())
        predicted_volume = float(pred_df["volume"].iloc[-1]) if "volume" in pred_df.columns else 0.0
        volume_spike_ratio = round(predicted_volume / avg_volume, 2) if avg_volume > 0 else 1.0

        return {
            "ticker": ticker,
            "predicted_return": round(predicted_return, 2),
            "signal": signal,
            "confidence": round(abs(predicted_return), 2),
            "last_close": round(last_close, 2),
            "predicted_close": round(predicted_close, 2),
            "pred_days": pred_days,
            "volume_spike_ratio": volume_spike_ratio,
        }
