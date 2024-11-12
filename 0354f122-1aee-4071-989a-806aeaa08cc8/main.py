from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import MACD, SMA, VWAP
from surmount.logging import log
import numpy as np

def SAM(ticker, data, cc_length=8, median_length=8, smooth_length=8):
    price_data = [i[ticker]['close'] for i in data]
    
    if len(price_data) < max(cc_length, median_length, smooth_length) + 3:
        return None

    price = np.array(price_data)

    def cyber_cycle(src, length):
        smooth = (src + 2 * np.roll(src, 1) + 2 * np.roll(src, 2) + np.roll(src, 3)) / 6
        cycle = np.zeros_like(smooth)
        for i in range(2, len(smooth)):
            cycle[i] = (1.0 - 0.5 * 0.707) * (smooth[i] - 2.0 * smooth[i-1] + smooth[i-2]) + 2.0 * 0.707 * cycle[i-1] - 0.707**2 * cycle[i-2]
        return cycle

    cc = cyber_cycle(price, cc_length)

    def dominant_cycle_period(cycle, med_len):
        real = cycle
        imag = np.roll(cycle, 1)
        period = np.zeros_like(cycle)
        for i in range(1, len(cycle)):
            if real[i] != 0 and real[i-1] != 0:
                delta_phi = (imag[i] / real[i] - imag[i-1] / real[i-1]) / (1 + imag[i] / real[i] * imag[i-1] / real[i-1])
                inst_period = 2 * np.pi / np.abs(delta_phi)
                period[i] = np.median(inst_period[max(0, i-med_len+1):i+1])
        return np.maximum(period, 2)

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

    return sam.tolist()

class TradingStrategy(Strategy):
    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return ["SPY", "QQQ", "AAPL", "GOOGL"]  # Add your desired assets

    def run(self, data):
        allocation_dict = {ticker: 0 for ticker in self.assets}
        price_data = data["ohlcv"]

        for ticker in self.assets:
            if len(price_data) < 150:  # Ensure we have enough data
                continue

            # Calculate indicators
            sam = SAM(ticker, price_data)
            macd = MACD(ticker, price_data, 12, 26, 9)
            ema_150 = SMA(ticker, price_data, 150)  # Using SMA as EMA might not be available
            vwap = VWAP(ticker, price_data)

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
            
            # Define your strategy conditions
            if (sam[-1] > 0 and  # SAM is positive
                macd['macd'][-1] > macd['signal'][-1] and  # MACD line above signal line
                current_price > ema_150[-1] and  # Price above 150-day EMA
                current_price > vwap[-1]):  # Price above VWAP
                
                allocation_dict[ticker] = 0.25  # Allocate 25% to this asset
                log(f"Buy signal for {ticker}")
            else:
                log(f"No signal for {ticker}")
            
            log("----------------------------")

        return TargetAllocation(allocation_dict)