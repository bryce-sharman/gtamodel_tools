CRS = 'EPSG_26917'

LENGTH_COL = 'length'
MODES_COL = 'modes'
TYPLE_COL = 'type'
LANES_COL = 'lanes'
VDF_COL = 'vdf'
FFSPD_COL = 'ul2'
LANECAP_COL = 'ul3'
AUTOVOL_COL = 'auto_volume'
AUTOADDVOL_COL = 'additional_volume'
AUTOTIME_COL = 'auto_time'

TRAFFIC_VKT_EXPR = "length * (auto_volume + additional_volume)"
TRAFFIC_VHT_EXPR = "timau * (auto_volume + additional_volume) / 60.0"
FILTER_VCR_EXPR = "((auto_volume + additional_volume) /  " \
                  "(lanes * data3)) > "

       