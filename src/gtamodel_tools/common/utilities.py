from datetime import time

def convert_mins_after_midnight_to_time(mins_after_midnight: int):
    """ Convert minutes after midnight to a datetime.time object.
    
    Args:
        mins_after_midnight: int
            Minutes after midnight (0-1439)
    Returns:
        datetime.time
            Corresponding time object
    
    """
    if mins_after_midnight >= 1440:
        print("Time value exceeds 1440 minutes, setting to 23:59")
        return time(hour=23, minute=59)
    hour = int(mins_after_midnight // 60)
    minute = int(mins_after_midnight - (60 * hour))
    return time(hour=hour, minute=minute)