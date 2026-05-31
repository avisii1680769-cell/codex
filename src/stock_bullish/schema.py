PRICE_COLUMNS = ("open", "high", "low", "close")
MARKET_COLUMNS = ("volume", "amount")
META_COLUMNS = (
    "trade_date",
    "symbol",
    "is_st",
    "is_suspended",
    "is_delisted",
    "listing_days",
    "industry",
    "market_cap",
)
REQUIRED_COLUMNS = ("trade_date", "symbol", *PRICE_COLUMNS, *MARKET_COLUMNS)

SIGNAL_DATE = "signal_date"
WINDOW = "window"
FIXED_TARGET_SUCCESS = "fixed_target_success"
PATH_SUCCESS = "path_success"
WINDOW_RETURN = "window_return"
