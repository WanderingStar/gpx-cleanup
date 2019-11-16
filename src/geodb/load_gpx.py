import argparse
from datetime import timezone

import gpxpy
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from geodb.model import GPSPoint, GPSTrack, db_url

ALL = object()
filtered_properties = {
    'extensions': [],
    'type_of_gpx_fix': 'none',
    'segments': ALL,
}


def slots_as_dict(obj):
    return {s: getattr(obj, s) for s in obj.__slots__ if hasattr(obj, s)}


def load_gpx(session, input_gpx):
    for track in input_gpx.tracks:
        # each GPX segment is a GPSTrack
        for i, segment in enumerate(track.segments):
            if len(track.segments) > 1:
                name = f"{track.name} {i + 1}"
            else:
                name = track.name
            print(f"track {track.name}")
            gps_track = GPSTrack(name=name, comment=track.comment, description=track.description,
                                 source=track.source, type=track.type)
            gps_track.properties = {
                k: v for k, v in slots_as_dict(track).items()
                if v is not None
                   and k not in gps_track.__dict__
                   and filtered_properties.get(k) != v
                   and filtered_properties.get(k) != ALL
            }
            session.add(gps_track)

            for point in segment.points:
                time = point.time
                if time.tzinfo is None:
                    time = time.replace(tzinfo=timezone.utc)
                gps_point = GPSPoint(
                    latitude=point.latitude,
                    longitude=point.longitude,
                    elevation=point.elevation,
                    time=time,
                    track=gps_track
                )
                gps_point.properties = {
                    k: v for k, v in slots_as_dict(point).items()
                    if v is not None
                       and k not in gps_point.__dict__
                       and filtered_properties.get(k) != v
                       and filtered_properties.get(k) != ALL
                }
                session.add(gps_point)

            session.commit()

    for point in input_gpx.waypoints:
        print(f"waypoint {point.name}")
        # each GPX waypoint is a GPSTrack with a single point
        time = point.time
        if time.tzinfo is None:
            time = time.replace(tzinfo=timezone.utc)
        gps_track = GPSTrack(name=point.name, comment=point.comment, description=point.description,
                             source=point.source, type=point.type or "Waypoint")
        gps_point = GPSPoint(
            latitude=point.latitude,
            longitude=point.longitude,
            elevation=point.elevation,
            time=time,
            track=gps_track
        )
        gps_point.properties = {
            k: v for k, v in slots_as_dict(point).items()
            if v is not None
               and k not in gps_track.__dict__
               and k not in gps_point.__dict__
               and filtered_properties.get(k) != v
        }
        session.add(gps_track)
        session.add(gps_point)

def load_gpx_files(files):
    engine = sqlalchemy.create_engine(db_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    for file in files:
        with open(file, 'r') as gpx_file:
            print(f"Loading {file}")
            input_gpx = gpxpy.parse(gpx_file)
            load_gpx(session, input_gpx)
            session.commit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='+', help="Path to GPX files to process")
    args = parser.parse_args()

    load_gpx_files(args.input)
