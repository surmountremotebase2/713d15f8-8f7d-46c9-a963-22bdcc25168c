from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA, VWAP
from surmount.logging import log

class TradingStrategy(Strategy):
    def __init__(self):
        # Specify the ticker of the stock you want to trade
        self.ticker = "AAPL"
    
    @property
    def assets(self):
        # The stock(s) to be included in the strategy
        return [self.ticker]

    @property
    def interval(self):
        # Set to hourly data
        return "1hour"
    
    def run(self, data):
        # Initialize allocation dictionary
        allocation_dict = {self.ticker: 0} # Start with no allocation
        
        # Check if there's enough data
        if len(data["ohlcv"]) < 5:
            log("Not enough data to execute strategy")
            return TargetAllocation(allocation_dict)
        
        # Calculate the 5-day SMA for the stock
        sma_value = SMA(self.ticker, data["ohlcv"], length=5)
        # Calculate VWAP for the current day
        vwap_value = VWAP(self.ticker, data["ohlcv"], length=5)
        
        # Last available price from data
        last_price = data["ohlcv"][-1][self.ticker]["close"]
        
        # Check if last price is greater than both the SMA and VWAP
        if last_price > sma_value[-1] and last_price > vwap_value[-1]:
            allocation_dict[self.ticker] = 1  # Allocate 100% to this stock
        elif last_price < sma_value[-1]:
            allocation_dict[self.ticker] = 0  # Allocate 0% to this stock
        
        # Return the target allocation
        return TargetAllocation(allocation_dict)