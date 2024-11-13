from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import MACD, SMA
from surmount.logging import log
import numpy as np

def SAM(ticker, data, cc_length=8, median_length=8, smooth_length=14):
    price_data = [i[ticker]['close'] for i in data]
    high_data = [i[ticker]['high'] for i in data]
    low_data = [i[ticker]['low'] for i in data]
    
    if len(price_data) < max(cc_length, median_length, smooth_length) + 3:
        log(f"Not enough data for SAM calculation for {ticker}")
        return None

    price = np.array(price_data)
    high = np.array(high_data)
    low = np.array(low_data)

    def cyber_cycle(src, length):
        smooth = (src + 2 * np.roll(src, 1) + 2 * np.roll(src, 2) + np.roll(src, 3)) / 6
        cycle = np.zeros_like(smooth)
        for i in range(2, len(smooth)):
            cycle[i] = (1.0 - 0.5 * 0.707) * (smooth[i] - 2.0 * smooth[i-1] + smooth[i-2]) + 2.0 * 0.707 * cycle[i-1] - 0.707**2 * cycle[i-2]
        return cycle

    def dominant_cycle_period(cycle, med_len):
        real = cycle
        imag = np.roll(cycle, 1)
        period = np.zeros_like(cycle)
        inst_periods = []

        for i in range(1, len(cycle)):
            if real[i] != 0 and real[i-1] != 0:
                delta_phi = (imag[i] / real[i] - imag[i-1] / real[i-1]) / (1 + imag[i] / real[i] * imag[i-1] / real[i-1])
                inst_period = 2 * np.pi / np.abs(delta_phi)
                inst_periods.append(inst_period)

                if len(inst_periods) >= med_len:
                    period[i] = np.median(inst_periods[-med_len:])
            else:
                inst_periods.append(np.nan)

        return np.maximum(period, 2)

    cc = cyber_cycle(price, cc_length)
    dc_period = dominant_cycle_period(cc, median_length)

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

    # Calculate ATR for normalization
    tr = np.maximum(high - low, np.abs(high - np.roll(price, 1)), np.abs(low - np.roll(price, 1)))
    atr = np.mean(tr[-14:])  # 14-period ATR

    # Normalize SAM by ATR and apply a scaling factor
    scaling_factor = 0.1  # Adjust this value to change the scale of SAM
    normalized_sam = (sam / atr) * scaling_factor

    # Apply a tanh function to bound the values between -1 and 1
    bounded_sam = np.tanh(normalized_sam)

    log(f"SAM calculation for {ticker}: min={np.min(bounded_sam)}, max={np.max(bounded_sam)}, mean={np.mean(bounded_sam)}")

    return bounded_sam.tolist()

def custom_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    # Calculate EMAs
    ema_fast = np.convolve(prices, np.ones(fast_period)/fast_period, mode='valid')
    ema_slow = np.convolve(prices, np.ones(slow_period)/slow_period, mode='valid')
    
    # Calculate MACD line
    macd_line = ema_fast[len(ema_fast) - len(ema_slow):] - ema_slow
    
    # Calculate Signal line
    signal_line = np.convolve(macd_line, np.ones(signal_period)/signal_period, mode='valid')
    
    # Adjust MACD line to match signal line length
    macd_line = macd_line[len(macd_line) - len(signal_line):]
    
    return {'macd': macd_line.tolist(), 'signal': signal_line.tolist()}

            # Use custom MACD function
            prices = [i[ticker]['close'] for i in price_data]
            macd_result = custom_macd(prices)
            
            if 'macd' not in macd_result or 'signal' not in macd_result:
                log(f"Custom MACD calculation failed for {ticker}")
                continue

class TradingStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.holdings = {ticker: 0 for ticker in self.assets}  # Initialize holdings

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

            log(f"Calculating MACD for {ticker}")
            prices = [i[ticker]['close'] for i in price_data]
            macd_result = custom_macd(prices)

            if 'macd' not in macd_result or 'signal' not in macd_result:
                log(f"MACD calculation failed for {ticker}")
                continue
                    
            ema_150 = SMA(ticker, price_data, length=150)  

            if sam is None or macd is None or ema_150 is None:
                continue

            current_price = price_data[-1][ticker]['close']
        
            # Logging for debugging
            log(f"--- Debug info for {ticker} ---")
            log(f"Current Price: {current_price}")
            log(f"SAM: {sam[-1]}")
            log(f"MACD: {macd['macd'][-1]}, Signal: {macd['signal'][-1]}")
            log(f"150-day EMA: {ema_150[-1]}")

            # Define your strategy conditions
            if (sam[-1] > 0 and 
                macd['macd'][-1] > macd['signal'][-1] and 
                current_price > ema_150[-1]):
                
                # Buy signal
                allocation_dict[ticker] = 0.25  
                self.holdings[ticker] = 0.25  # Update holdings
                log(f"Buy signal for {ticker}")
            
            elif self.holdings[ticker] > 0:
                # Hold if already holding the asset
                allocation_dict[ticker] = self.holdings[ticker]
                log(f"Holding position for {ticker}")

            else:
                log(f"No signal for {ticker}")

            log("----------------------------")

        return TargetAllocation(allocation_dict)