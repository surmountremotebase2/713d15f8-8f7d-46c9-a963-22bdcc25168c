import numpy as np
from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import MACD, SMA, VWAP
from surmount.logging import log

# Define the SAM function
def SAM(ticker, data, cc_length=8, median_length=8, smooth_length=8):
    price_data = [i[ticker]['close'] for i in data]
    
    if len(price_data) < max(cc_length, median_length, smooth_length) + 3:
        return None

    price = np.array(price_data)

    # Define the Cyber Cycle function
    def cyber_cycle(src):
        smooth = (src + 2 * np.roll(src, 1) + 2 * np.roll(src, 2) + np.roll(src, 3)) / 6
        cycle = np.zeros_like(smooth)
        for i in range(2, len(smooth)):
            cycle[i] = (1.0 - 0.5 * 0.707) * (smooth[i] - 2.0 * smooth[i-1] + smooth[i-2]) + \
                        2.0 * 0.707 * cycle[i-1] - 0.707**2 * cycle[i-2]
        return cycle

    # Define the Dominant Cycle Period function
    def dominant_cycle_period(cycle):
        real = cycle
        imag = np.roll(cycle, 1)
        period = np.zeros_like(cycle)
        inst_periods = []  

        for i in range(1, len(cycle)):
            if real[i] != 0 and real[i-1] != 0:
                delta_phi = (imag[i] / real[i] - imag[i-1] / real[i-1]) / \
                             (1 + imag[i] / real[i] * imag[i-1] / real[i-1])
                inst_period = 2 * np.pi / np.abs(delta_phi)
                inst_periods.append(inst_period)  
                
                if len(inst_periods) >= median_length:
                    period[i] = np.median(inst_periods[-median_length:])  
            else:
                inst_periods.append(np.nan)

        return np.maximum(period, 2)

    cc = cyber_cycle(price)
    dc_period = dominant_cycle_period(cc)

    lookback = np.round(dc_period).astype(int) - 1
    value = price - np.roll(price, lookback)

    a1 = np.exp(-1.414 * np.pi / smooth_length)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / smooth_length)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    sam = np.zeros_like(value)
    for i in range(2, len(value)):
        sam[i] = c1 * value[i] + c2 * sam[i-1] + c3 * sam[i-2]

    return sam.tolist()

from datetime import datetime

def VWAP(ticker, price_data, length):
    # Assuming 'data' is passed as price_data
    dates = []
    for i in price_data:
        try:
            date_str = i[ticker]["date"]
            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')  # Updated format
            dates.append(date_obj)
        except ValueError as e:
            print(f"Error parsing date '{date_str}': {e}")
    
    # Continue with VWAP calculation...



# Define your trading strategy class
class TradingStrategy(Strategy):
    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return ["AAPL"]  

    def run(self, data):
        allocation_dict = {ticker: 0 for ticker in self.assets}
        price_data = data["ohlcv"]

        for ticker in self.assets:
            if len(price_data) < max(150, 14):  
                continue

            # Calculate indicators
            sam = SAM(ticker, price_data)
            macd = MACD(ticker, price_data, fast=12, slow=26)
            ema_150 = SMA(ticker, price_data, length=150)  
            vwap = VWAP(ticker, price_data, length=14)

            if sam is None or macd is None or ema_150 is None or vwap is None:
                continue

            current_price = price_data[-1][ticker]['close']
        
            # Logging for debugging
            log(f"--- Debug info for {ticker} ---")
            log(f"Current Price: {current_price}")
            log(f"SAM: {sam[-1]}")
            log(f"MACD: {macd['macd'][-1]}, Signal: {macd['signal'][-1]}")
            log(f"150-day EMA: {ema_150[-1]}")
            log(f"VWAP: {vwap[-1]}")
        
             # Define your buy conditions
            if (sam[-1] > 0 and 
                macd['macd'][-1] > macd['signal'][-1] and 
                current_price > ema_150[-1] and 
                current_price > vwap[-1]):
                
                allocation_dict[ticker] = 0.25  # Allocate 25% to this asset  
                log(f"Buy signal for {ticker}")

            # Define your sell condition
            elif current_price < ema_150[-1]:  # Price drops below the 150-day SMA
                allocation_dict[ticker] = 0.0  # Sell all or reduce position to zero
                log(f"Sell signal for {ticker} - Price below 150-day SMA")

            else:
                log(f"No action for {ticker}")
            
            log("----------------------------")

        return TargetAllocation(allocation_dict)