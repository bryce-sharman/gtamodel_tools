# MicroSim Enums for GTAModel v4.2

import numpy as np
import pandas as pd


TIME_PERIOD_DEFINITIONS = {
    'ON': {
        'start': 0.0,     # 00:00
        'end': 360.0      # 06:00
    },
    'AM': {
        'start': 360.0,   # 06:00
        'end': 540.0      # 09:00
    },
    'MD': {
        'start': 540.0,   # 09:00
        'end': 900.0      # 15:00
    },
    'PM': {
        'start': 900.0,   # 15:00
        'end':  1140.0    # 19:00
    },
    'EV': {
        'start': 1140.0,  # 19:00,
        'end': 1440.0     # 24:00,
    }
}

N_TRIPMODE_SAMPLES = 10