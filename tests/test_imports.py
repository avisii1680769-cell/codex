from stock_bullish.config import BacktestConfig
from stock_bullish.schema import PRICE_COLUMNS


def test_package_imports_config_and_schema():
    config = BacktestConfig()
    assert config.windows == (5, 20, 60)
    assert "close" in PRICE_COLUMNS
