import pandas as pd

CRS = 'EPSG:26917'
GRID_OFFSET = 17   # degrees

LENGTH_COL = 'length'
MODES_COL = 'modes'
TYPE_COL = 'type'
LANES_COL = 'lanes'
VDF_COL = 'vdf'
FFSPD_COL = 'ul2'
LANECAP_COL = 'ul3'
AUTOVOL_COL = 'auto_volume'
AUTOADDVOL_COL = 'additional_volume'
TRAFFIC_VOL = f'({AUTOVOL_COL} + {AUTOADDVOL_COL})'
AUTOTIME_COL = 'auto_time'

TRBOARDINGS_COL = 'boardings'
TRALIGHTINGS_COL = 'alightings'
TRONBOARD_COL = 'volume'

MIN_REGNODE_ID = 10000
AUTO_MODE = 'c'

TRAFFIC_RESULTS_COLNAMES = [AUTOVOL_COL, AUTOADDVOL_COL, AUTOTIME_COL]
TRANSIT_RESULTS_COLNAMES  = [TRBOARDINGS_COL, TRALIGHTINGS_COL, TRONBOARD_COL]

LINK_CLASSIFICATION_EXPRS = {
    'freeway': {
        'attr': VDF_COL,
        'values': [11, 12],
    },
    'exclusive': {
        'attr': VDF_COL,
        'values': [14, 16, 41]
    },
    'ramp': {
        'attr': VDF_COL,
        'values': [13, 15, 17]
    },
    'arterial': {
        'attr': VDF_COL,
        'values': [20, 21, 30, 40, 42, 50]
    },
    'collector': {
        'attr': VDF_COL,
        'values': [22, 31, 51]
    },
    'connector': {
        'attr': VDF_COL,
        'values': [90]
    }
}


ZONE_RANGES = [
            ('unassigned', 1, 999), 
            ('Toronto', 1000, 1999), 
            ('Durham', 2000, 2999),
            ('York', 3000, 3999),
            ('Peel', 4000, 4999),
            ('Halton', 5000, 5999),
            ('Hamilton', 6000, 6999),
            ('Niagara', 7000, 7199),
            ('Reserved', 7200, 7999),
            ('Haldimand-Norfolk', 8000, 8099),
            ('Brant', 8100, 8199),
            ('Waterloo', 8200, 8499),
            ('Wellington', 8500, 8699),
            ('Dufferin', 8700, 8799),
            ('Simcoe',  8800, 8999),
            ('Kawartha Lakes', 9000, 9099),
            ('Peterborough', 9100, 9299),
            ('Northumberland', 9300, 9399),
            ('Gateways', 9400, 9499),
            ('Stations', 9500, 9999)
        ]

NODE_RANGES = [
            ('centroid', 0, 9999), 
            ('Toronto', 10000, 19999), 
            ('Durham', 20000, 29999),
            ('York', 30000, 39999),
            ('Peel', 40000, 49999),
            ('Halton', 50000, 59999),
            ('Hamilton', 60000, 69999),
            ('Niagara', 70000, 79999),
            ('Haldimand-Norfolk',  80000, 80999),
            ('Brant',  81000, 81999),
            ('Waterloo',  82000, 84999),
            ('Wellington',  85000, 86999),
            ('Dufferin',  87000, 87999),
            ('Simcoe',  88000, 89999),
            ('Kawartha Lakes', 90000, 90999),
            ('Peterborough', 91000, 91999),
            ('External zones/gateways Canada', 94000, 94999),
            ('External zones/gateways, US', 95000, 95999),
            ('BRT/LRT platform', 96000, 96999),
            ('Subway platform',  97000, 97999),
            ('GO Rail platform',  98000, 98999),
            ('Hypernetwork nodes', 100000, 899999),
            ('HOV',  900000, 999999)
        ]

TRANSIT_OPERATORS = pd.DataFrame.from_records(
        columns=['operator', 'regex_expr'],
        data = [
            ('Durham', '^D'),
            ('Burlington', '^HB'),
            ('Oakville', '^HO'),
            ('Milton', '^HM'),
            ('Brampton', '^B'),
            ('MiWay', '^M'),
            ('Hamilton', '^W'),
            ('YRT (not Viva)', '^Y^V'),
            ('YRT (Viva)', '^YV'),
            ('TTC (Subway)', '^TS'),
            ('TTC (not Subway)', '^T^S'),
            ('GO Bus', 'GB'),
            ('GO Train', 'GT'),
            ('Link Train', '^L')
        ]
    )

