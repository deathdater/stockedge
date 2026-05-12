"""Cross-module data contracts and pipeline sequencing.

Dependencies:
- market_data.DailyCandle -> features.DailyFeature
- market_data.DailyCandle -> labels.PredictionLabel
- features.DailyFeature + labels.PredictionLabel -> ml_models.ModelRun
- ml_models outputs -> ensemble score rows
- ensemble score rows -> rankings.DailyRanking
- rankings + market_data -> backtesting results
- live features/predictions -> monitoring drift hooks

Task sequencing:
1) ingest candles
2) compute leakage-safe features
3) compute future-return labels
4) train specialized models with walk-forward folds
5) infer component scores (trend/volatility/risk/confidence)
6) compute ensemble score and persist daily ranking
7) run backtests and persist summaries
8) run monitoring drift/reporting hooks
"""
