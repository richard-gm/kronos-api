-- Run once in Supabase → SQL Editor

create table if not exists kronos_scores (
  ticker           text primary key,
  predicted_return numeric,          -- percentage, e.g. 3.42 means +3.42%
  signal           text,             -- BULLISH | NEUTRAL | BEARISH
  confidence       numeric,          -- abs(predicted_return), used for sorting
  last_close       numeric,
  predicted_close  numeric,
  pred_days        int,
  run_at           timestamptz default now()
);

create index if not exists kronos_scores_run_at on kronos_scores (run_at desc);
