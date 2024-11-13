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

class TradingStrategy(Strategy):
    def __init__(self):
        self.holding = {}

    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return ["CVX", "PR", "AAPL", "GOOGL", "NVDA"]

    def run(self, data):
        allocation_dict = {ticker: 0 for ticker in self.assets}
        price_data = data["ohlcv"]

        # Initialize holding status for any new assets
        for ticker in self.assets:
            if ticker not in self.holding:
                self.holding[ticker] = False

        for ticker in self.assets:
            if len(price_data) < 150:  # Ensure we have enough data
                continue

            # Calculate indicators
            sam = SAM(ticker, price_data)
            macd = MACD(ticker, price_data, 12, 26)
            ema_150 = SMA(ticker, price_data, 150)  

            if sam is None or macd is None or ema_150 is None:
                continue

            current_price = price_data[-1][ticker]['close']
            
            # Extract MACD values
            macd_line = macd['MACD_12_26_9'][-1]
            signal_line = macd['MACDs_12_26_9'][-1]
            
            # Logging for debugging
            log(f"--- Debug info for {ticker} ---")
            log(f"Current Price: {current_price}")
            log(f"SAM: {sam[-1]}")
            log(f"MACD line: {macd_line}, Signal line: {signal_line}")
            log(f"150-day EMA: {ema_150[-1]}")
            log(f"Holding: {self.holding[ticker]}")

            # Entry condition
            if not self.holding[ticker] and (sam[-1] > 0 and
                macd_line > signal_line and 
                current_price > ema_150[-1]):  
                
                allocation_dict[ticker] = 0.10
                self.holding[ticker] = True
                log(f"Buy signal for {ticker}")

            # Exit condition
            elif self.holding[ticker] and current_price < ema_150[-1]:
                allocation_dict[ticker] = 0.0
                self.holding[ticker] = False
                log(f"Sell signal for {ticker} - Price below 150-day SMA")

            # Holding condition
            elif self.holding[ticker]:
                allocation_dict[ticker] = 0.10
                log(f"Holding {ticker}")

            else:
                log(f"No action for {ticker}")
            
            log("----------------------------")

        return TargetAllocation(allocation_dict)