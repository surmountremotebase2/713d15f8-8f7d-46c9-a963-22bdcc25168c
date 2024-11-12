import numpy as np
import pandas as pd
from surmount.technical_indicators import SMA
from surmount.data import Data

def SAM(ticker, data, cc_length=8, median_length=8, smooth_length=8):
    price_data = [i[ticker]['close'] for i in data]
    
    if len(price_data) < max(cc_length, median_length, smooth_length) + 3:
        return None

    # Convert to numpy array for faster calculations
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

class MyStrategy(Strategy):
    def __init__(self):
        self.data_list = [Data.OHLCV(ticker) for ticker in self.assets]

    def run(self, data):
        allocation_dict = {ticker: 0 for ticker in self.assets}

        for ticker in self.assets:
            price_data = data["ohlcv"]
            
            sam = SAM(ticker, price_data)
            
            if sam is not None and len(sam) > 1:
                if sam[-1] > 0 and sam[-2] <= 0:  # Crossover above zero
                    allocation_dict[ticker] = 0.2  # Allocate 20% to this asset
                elif sam[-1] < 0 and sam[-2] >= 0:  # Crossover below zero
                    allocation_dict[ticker] = -0.2  # Short 20% of this asset

        return TargetAllocation(allocation_dict)