from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA
from surmount.logging import log
from surmount.data import Asset

class TradingStrategy(Strategy):
    def __init__(self):
        self.ticker = "AAPL"

    @property
    def interval(self):
        # Using daily data interval for SMA calculations.
        return "1day"

    @property
    def assets(self):
        # Strategy is focusing on a single asset.
        return [self.ticker]

    @property
    def data(self):
        # No additional data requirements specified for this strategy.
        return []

    def run(self, data):
        # Retrieve ohlcv (open-high-low-close-volume) data for calculations.
        ohlcv_data = data["ohlcv"]
        
        # Calculating the 5-day and 13-day SMA for the asset.
        sma_5 = SMA(self.ticker, ohlcv_data, 5)
        sma_13 = SMA(self.ticker, ohlcv_data, 13)
        
        if len(sma_5) == 0 or len(sma_13) == 0:
            # If there are not enough data points to calculate SMA, do not allocate to this asset.
            return TargetAllocation({})
        
        # The latest closing price of the ticker.
        latest_close_price = ohlcv_data[-1][self.ticker]["close"]
        
        # Decision logic for entering and exiting the trade.
        if latest_close_price > sma_5[-1] and latest_close_price < sma_13[-1]:
            # If price crosses above the 5-day SMA and is still below the 13-day SMA, go long.
            allocation = 1.0
        elif latest_close_price < sma_13[-1]:
            # If price crosses below the 13-day SMA, exit the trade.
            allocation = 0.0
        else:
            # For other conditions, maintain previous position.
            # In a real trading scenario, you would access and consider current holdings
            # to decide whether to maintain, increase, or decrease your position.
            allocation = 0.0  # Adjust as needed based on your portfolio management logic.

        # Logging for debugging
        log(f"Latest Close: {latest_close_price}, SMA 5: {sma_5[-1]}, SMA 13: {sma_13[-1]}, Allocation: {allocation}")

        return TargetAllocation({self.ticker: allocation})