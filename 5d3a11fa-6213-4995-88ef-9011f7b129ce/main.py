from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA
from surmount.data import OHLCV

class TradingStrategy(Strategy):
    
    def __init__(self):
        # Define which ticker this strategy will apply to
        self.ticker = "AAPL"
        
    @property
    def assets(self):
        # Strategy is applied to a single asset
        return [self.ticker]
        
    @property
    def interval(self):
        # Using 1-day interval for SMA calculation,
        # 1-hour price checks will require separate handling
        return "1day"
      
    def run(self, data):
        # Calculate 5-day and 13-day SMA
        sma_5_day = SMA(self.ticker, data, 5)
        sma_13_day = SMA(self.ticker, data, 13)
        
        # Latest daily close price for exit check
        daily_close_price = data["ohlcv"][-1][self.ticker]["close"]
        
        # Allocation decision, initially none (maintaining current position)
        allocation = {"AAPL": 0}
        
        # Ensure we have at least 13 days of data to make a decision
        if len(sma_13_day) >= 13 and len(sma_5_day) >= 5:
            # Exit condition check - if daily price is lower than 13-day SMA
            if daily_close_price < sma_13_day[-1]:
                allocation = {"AAPL": 0}  # Exit trade, zero allocation
            # Entry condition - Due to the limitation mentioned before,
            # the "30-minute higher than 5-day and 13-day SMA" condition
            # gets simplified to checking if the daily closing is higher
            # than both SMAs
            elif daily_close_price > sma_5_day[-1] and daily_close_price > sma_13_day[-1]:
                allocation = {"AAPL": 1}  # Enter or maintain full position
            
        # Return the target allocation based on the conditions
        return TargetAllocation(allocation)
# Unable to generate strategy