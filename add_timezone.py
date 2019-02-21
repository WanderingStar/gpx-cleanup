import dateutil.parser
import requests
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from model import db_url, GPSTrack, postgres_timezone
from secrets import azure_key


def localtime_for_point(gps_point):
    params = {
        "subscription-key": azure_key,
        "api-version": "1.0",
        "options": "all",
        "query": f"{gps_point.latitude},{gps_point.longitude}",
        "timeStamp": gps_point.time.isoformat()
    }
    r = requests.get("https://atlas.microsoft.com/timezone/byCoordinates/json", params=params)
    r.raise_for_status()
    local = dateutil.parser.parse(r.json()["TimeZones"][0]["ReferenceTime"]["WallTime"])
    print(f"{gps_point.time.isoformat()}\t{gps_point.track.name}\t{local}")
    return local


def add_tz_to_points(points):
    tz0 = points[0].tz or postgres_timezone(localtime_for_point(points[0]).tzinfo)
    points[0].tz = tz0
    tzN = points[-1].tz or postgres_timezone(localtime_for_point(points[-1]).tzinfo)
    points[-1].tz = tzN
    if len(points) < 3:
        return
    if tz0 == tzN:
        for point in points[1:-1]:
            point.tz = points[0].tz
    else:
        midpoint = len(points) // 2
        add_tz_to_points(points[0:midpoint])
        add_tz_to_points(points[midpoint:])


if __name__ == '__main__':
    engine = sqlalchemy.create_engine(db_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    for gps_track in session.query(GPSTrack):
        if not gps_track.points:
            continue
        if gps_track.points[0].tz:
            # print(f"\t{gps_track.name} has tz")
            continue
        print(f"{gps_track.name}: {len(gps_track.points)}")
        add_tz_to_points(gps_track.points)
        for point in gps_track.points:
            session.add(point)
        session.commit()
