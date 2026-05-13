-- Run once in Supabase → SQL Editor
-- Creates the portfolio_tickers table and seeds it with all current analysis tickers.
-- After this, Kronos reads from this table instead of the PORTFOLIO_TICKERS env var.

create table if not exists portfolio_tickers (
  ticker    text primary key,
  source    text not null default 'analysis',  -- 'analysis' | 'custom'
  added_at  timestamptz default now()
);

-- Seed with all current analysis tickers from the stock dashboard JSON files
insert into portfolio_tickers (ticker, source) values
  ('AMAT', 'analysis'),
  ('ANET', 'analysis'),
  ('BB',   'analysis'),
  ('BE',   'analysis'),
  ('CDE',  'analysis'),
  ('CEG',  'analysis'),
  ('CL',   'analysis'),
  ('CRWD', 'analysis'),
  ('CRWV', 'analysis'),
  ('DDOG', 'analysis'),
  ('DLR',  'analysis'),
  ('EQIX', 'analysis'),
  ('FCX',  'analysis'),
  ('FLNC', 'analysis'),
  ('IREN', 'analysis'),
  ('KTOS', 'analysis'),
  ('MDB',  'analysis'),
  ('MRVL', 'analysis'),
  ('NBIS', 'analysis'),
  ('NOK',  'analysis'),
  ('NOW',  'analysis'),
  ('OKLO', 'analysis'),
  ('ONDS', 'analysis'),
  ('ORCL', 'analysis'),
  ('PATH', 'analysis'),
  ('PLTR', 'analysis'),
  ('POET', 'analysis'),
  ('RGTI', 'analysis'),
  ('SMR',  'analysis'),
  ('SOFI', 'analysis'),
  ('VRT',  'analysis'),
  ('ZS',   'analysis')
on conflict (ticker) do nothing;

-- Also pull in any tickers already saved as custom_tickers
insert into portfolio_tickers (ticker, source)
select ticker, 'custom' from custom_tickers
on conflict (ticker) do nothing;
