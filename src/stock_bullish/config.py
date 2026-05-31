from dataclasses import dataclass, field


@dataclass(frozen=True)
class CostConfig:
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0005


@dataclass(frozen=True)
class FilterConfig:
    exclude_st: bool = True
    exclude_suspended: bool = True
    exclude_delisted: bool = True
    min_listing_days: int = 120
    liquidity_lookback: int = 20
    min_avg_amount: float = 30_000_000


@dataclass(frozen=True)
class BacktestConfig:
    windows: tuple[int, ...] = (5, 20, 60)
    fixed_return_targets: dict[int, float] = field(
        default_factory=lambda: {5: 0.03, 20: 0.08, 60: 0.15}
    )
    stop_loss: float = 0.04
    take_profit_loss_ratio: float = 2.0
    costs: CostConfig = field(default_factory=CostConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
