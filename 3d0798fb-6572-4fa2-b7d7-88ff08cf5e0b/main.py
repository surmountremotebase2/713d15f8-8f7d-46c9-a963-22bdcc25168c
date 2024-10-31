from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA
from surmount.logging import log
from surmount.data import OHLCV

class TradingStrategy(Strategy):
    def __init__(self):
        self.tickers = ["SPY"]

    @property
    def interval(self):
        # Specifying the interval for the trading strategy. The OHLCV data interval must match the strategy's operation, thus using "30min" for price checks.
        return "30min"  

    @property
    def assets(self):
        return self.tickers

    def run(self, data):
        # Initialize allocation dictionary with zero allocation.
        allocation_dict = {ticker: 0 for ticker in self.tickers}

        # Calculate 5-day and 13-day SMA for SPY. The data is in 30-minute intervals, so to get an approximation of a "day", you would consider the number of 30-minute sessions in a trading day. 
        # Assuming a standard 6.5 hour trading day, there are 13 periods of 30 minutes in each day. Thus, 5-day SMA would require 5*13 = 65 periods and 13-day SMA requires 13*13 = 169 periods.
        sma_5_day = SMA("SPY", data["ohlcv"], 65) # Approximation using the number of 30-minute intervals in 5 trading days.
        sma_13_day = SMA("SPY", data["ohlcv"], 169) # Approximation using the number of 30-minute intervals in 13 trading days.
        
        if len(sma_5_day) > 0 and len(sma_13_day) > 0:
            # Current price is the close of the last available 30-minute period.
            current_price = data["ohlcv"][-1]["SPY"]['close']

            # Check if the current price is greater than both the 5-day and 13-day SMAs.
            if current_price > sma_5_day[-1] and current_price > sma_13_day[-1]:
                allocation_dict["SPY"] = 1 # Enter trade (fully allocate)
            elif current_price < sma_13_day[-1]:
                allocation_dict["SPY"] = 0 # Exit trade (no allocation)

        return TargetAllocation(allocation_dict)