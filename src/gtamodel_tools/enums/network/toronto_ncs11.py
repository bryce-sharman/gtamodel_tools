import gtamodel_tools.common.spatial_aggregator as sa

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
        'values': [22, 43, 51]
    },
    'connector': {
        'attr': VDF_COL,
        'values': [90]
    }
}

ZONE_RANGES = sa.create_spatial_aggregator(
        'custom_ranges', 
        ranges=[
            ('Toronto', 0, 1000), 
            ('Durham', 1001, 2000),
            ('York', 2001, 3000),
            ('Peel', 3001, 4000),
            ('Halton', 4001, 5000),
            ('Hamilton', 5001, 6000),
            ('External', 6001, 7000),
            ('Undefined', 7001, 9699),
            ('Subway_stations', 9700, 9799),
            ('GORail_stations', 9800, 9999)
        ],
        ids=range(0, 10000),
        name='zone_regions',
    )

NODE_RANGES = sa.create_spatial_aggregator(
        'custom_ranges', 
        ranges=[
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
            ('Wellington' ,  85000, 86999),
            ('Dufferin' ,  87000, 87999),
            ('Simcoe',  88000, 89999),
            ('Kawartha Lakes', 90000, 90999),
            ('Peterborough', 91000, 91999),
            ('External zones/gateways Canada', 94000, 94999),
            ('External zones/gateways, US', 95000, 95999),
        ],
        ids=range(0, 1000000),
        name='zone_regions',
    )

