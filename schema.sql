-- Run once in Supabase → SQL Editor

create table if not exists kronos_scores (
  ticker               text primary key,
  predicted_return     numeric,          -- percentage, e.g. 3.42 means +3.42%
  signal               text,             -- BULLISH | NEUTRAL | BEARISH
  confidence           numeric,          -- abs(predicted_return), used for sorting
  last_close           numeric,
  predicted_close      numeric,
  pred_days            int,
  volume_spike_ratio   numeric,          -- predicted volume / 20-day avg volume
  run_at               timestamptz default now()
);

-- Migration: add volume_spike_ratio to existing tables
alter table kronos_scores add column if not exists volume_spike_ratio numeric;

create index if not exists kronos_scores_run_at on kronos_scores (run_at desc);
