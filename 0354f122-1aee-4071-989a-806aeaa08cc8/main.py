from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import MACD, SMA
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

    return sam.tolist()

class TradingStrategy(Strategy):
    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return ["SPY", "QQQ", "AAPL", "GOOGL"]

    def run(self, data):
        allocation_dict = {ticker: 0 for ticker in self.assets}
        price_data = data["ohlcv"]

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
            
            # Log full indicator outputs
            log(f"--- Debug info for {ticker} ---")
            log(f"Current Price: {current_price}")
            log(f"SAM: {sam[-1]}")
            log(f"Full MACD output: {macd}")
            log(f"150-day EMA: {ema_150[-1]}")

            # Attempt to extract MACD and Signal lines
            macd_line = None
            signal_line = None

            if isinstance(macd, dict):
                macd_line = macd.get('macd', [])[-1] if macd.get('macd') else None
                signal_line = macd.get('signal', [])[-1] if macd.get('signal') else None
            elif isinstance(macd, (list, tuple)) and len(macd) >= 2:
                macd_line = macd[0]
                signal_line = macd[1]

            log(f"MACD line: {macd_line}, Signal line: {signal_line}")

            # Entry condition
            if (sam[-1] > 0 and
                macd_line is not None and signal_line is not None and
                macd_line > signal_line and 
                current_price > ema_150[-1]):  
                
                allocation_dict[ticker] = 0.25  
                log(f"Buy signal for {ticker}")

            # Sell condition when price drops below the 150-day SMA
            elif current_price < ema_150[-1]:
                allocation_dict[ticker] = 0.0  
                log(f"Sell signal for {ticker} - Price below 150-day SMA")

            else:
                log(f"No action for {ticker}")
            
            log("----------------------------")

        return TargetAllocation(allocation_dict)