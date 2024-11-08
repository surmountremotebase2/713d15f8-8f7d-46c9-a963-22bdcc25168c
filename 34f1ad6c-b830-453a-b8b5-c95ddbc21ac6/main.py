from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA
from surmount.data import OHLCV

class TradingStrategy(Strategy):
    def __init__(self):
        self.ticker = "AAPL"

    @property
    def assets(self):
        return [self.ticker]

    @property
    def interval(self):
        # Since Surmount does not support 30min intervals directly as per the examples,
        # '1hour' is used for a closely relevant timeframe.
        # Adjustments may be needed for exact 30min logic.
        return "1hour"

    def run(self, data):
        # Extract the 'close' prices for the asset
        closes = [d[self.ticker]["close"] for d in data["ohlcv"]]

        # Calculate the 5-day SMA for the asset. Note: Adjust '5' accordingly if you change the interval or need dynamic window size based on data availability.
        sma_5 = SMA(self.ticker, data["ohlcv"], 5)
        
        # Determine the current price
        current_price = closes[-1] if len(closes) > 0 else None

        # Check if current price is greater than the 5-day SMA for buying,
        # Sell (set allocation to 0) when below the 5-day SMA.
        # Note: '1' signifies full allocation to AAPL, '0' signifies no allocation.
        allocation = 0
        if current_price and len(sma_5) > 0 and current_price > sma_5[-1]:
            allocation = 1  # Buy or hold the position
        elif current_price and sma_5 and current_price < sma_5[-1]:
            allocation = 0  # Sell or not hold the position
        
        # Return the computed allocation
        return TargetAllocation({self.ticker: allocation})

# Note: This code is a template, make sure to adjust the interval or trading logic to fit the 30-minute requirement or any other specific conditions you have.