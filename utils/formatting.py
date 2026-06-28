import pytz

_est = pytz.timezone("America/New_York")


def to_est(dt):
    return dt.replace(tzinfo=pytz.utc).astimezone(_est)
