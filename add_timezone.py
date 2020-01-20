import dateutil.parser
import requests
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from geodb.model import db_url, GPSTrack, GPSPoint
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
    if points[0].tz is None:
        points[0].set_timezone(localtime_for_point(points[0]).tzinfo)
    if points[-1].tz is None:
        points[-1].set_timezone(localtime_for_point(points[-1]).tzinfo)
    if len(points) < 3:
        return
    if points[0].tz == points[-1].tz:
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

    track_ids = session.query(GPSPoint).filter(GPSPoint.tz == None).distinct(GPSPoint.track_id).all()
    print(f"{len(track_ids)} tracks are missing time zones")

    for gps_track in session.query(GPSTrack).filter(GPSTrack.id.in_(track_ids)):
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
