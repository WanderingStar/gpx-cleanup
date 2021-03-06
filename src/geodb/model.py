import os
import re
from datetime import timezone, timedelta

import sqlalchemy
from geojson import Feature, LineString, Point
from ipyleaflet import Polyline
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
import gpxpy.gpx


def db_url():
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASS')
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    database = os.environ.get('DB_DATABASE', 'postgres')
    return f'postgresql://{user}:{password}@{host}:{port}/{database}'


class GPSTrack(Base):
    __tablename__ = 'track'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    comment = Column(String)
    description = Column(String)
    source = Column(String)
    type = Column(String)
    filename = Column(String)

    properties = Column(JSONB)
    raw = Column(JSONB)
    parent_id = Column(Integer, ForeignKey('track.id', ondelete="SET NULL"))
    parent = relationship('GPSTrack', remote_side=[id])

    points = relationship('GPSPoint', order_by='GPSPoint.time', back_populates='track')

    @property
    def start(self):
        if not self.points:
            return None
        return self.points[0]

    @property
    def end(self):
        if not self.points:
            return None
        return self.points[-1]

    @property
    def is_east(self):
        if not self.points:
            return None
        return self.start.is_east

    @property
    def bounds(self):
        min_lat, min_lon = self.start.corrected_coords(self.is_east)[0:2]
        max_lat, max_lon = min_lat, min_lon
        for p in self.points:
            coords = p.corrected_coords(self.is_east)[0:2]
            min_lat = min(min_lat, coords[0])
            min_lon = min(min_lon, coords[1])
            max_lat = max(max_lat, coords[0])
            max_lon = max(max_lon, coords[1])
        return (min_lat, min_lon, max_lat, max_lon)

    def as_geojson_feature(self, east):
        props = dict(self.properties or {})
        props.update({
            'track_id': self.id,
            'name': self.name,
            'comment': self.comment,
            'description': self.description,
            'source': self.source,
            'type': self.type,
            'start': str(self.start.localtime),
            'end': str(self.end_localtime),
        })
        props = {k: v for k, v in props.items() if v is not None}
        if len(self.points) == 1:
            p = self.start
            return Feature(geometry=Point(p.corrected_coords(east)),
                           properties=props)

        east = east if east is not None else self.is_east
        return Feature(
            geometry=LineString([p.corrected_coords(east) for p in self.points]),
            properties=props)

    # returns a multi-polyline if there are antimeridian crossings
    def as_polyline(self, start=None, end=None, **kwargs):
        # filter points by start and end time
        points = [p.lat_lon for p in self.points
                  if (start is None or p.time >= start) and (end is None or p.time <= end)]
        lines = []
        # reversed so as not to interrupt the iteration when we reassign points
        for i in reversed(range(1, len(points))):
            lat_1, lon_1 = points[i]
            lat_2, lon_2 = points[i - 1]
            # if this pair of points crosses the antimeridian, break the track
            # into two tracks, one on each side of the globe, with an artificial
            # point added (m, the middle point) at the antimeridian
            if abs(lon_1 - lon_2) > 180:
                if lon_1 > 0:
                    lon_2 += 360.
                    lon_m = 180.
                else:
                    lon_2 -= 360.
                    lon_m = -180.
                f = (lon_m - lon_1) / (lon_2 - lon_1)
                lat_m = lat_1 + f * (lat_2 - lat_1)
                lines.append([[lat_m, lon_m]] + points[i:])
                points = points[0:i] + [[lat_m, -lon_m]]
        lines.append(points)
        return Polyline(locations=list(reversed(lines)), **kwargs)

    def as_gpxpy(self):
        if len(self.points) == 1:
            p = self.start
            w = gpxpy.gpx.GPXWaypoint(
                latitude=p.latitude, longitude=p.longitude, elevation=p.elevation,
                time=p.time, name=self.name, description=self.description, type=self.type,
                comment=self.source or self.filename
            )
            return w
        t = gpxpy.gpx.GPXTrack(name=self.name, description=self.description)
        s = gpxpy.gpx.GPXTrackSegment()
        t.segments.append(s)
        for p in self.points:
            s.points.append(gpxpy.gpx.GPXTrackPoint(
                latitude=p.latitude, longitude=p.longitude, elevation=p.elevation, time=p.time))
        return t

    def section(self, start, end):
        if self.start.time >= start and self.end.time <= end:
            return self
        track = clone_model(self)
        track.parent = self
        track.points = [clone_model(p, track=track) for p in self.points
                        if p.time >= start and p.time <= end]
        if len(track.points) == 0:
            return None
        return track

    def __str__(self):
        return f"<GPSTrack {self.name or self.filename or self.id}>"



class GPSPoint(Base):
    __tablename__ = 'point'

    id = Column(Integer, primary_key=True)
    latitude = Column(Numeric, nullable=False)
    longitude = Column(Numeric, nullable=False)
    elevation = Column(Numeric, nullable=True)
    time = Column(DateTime(timezone=True))  # one would think that this stores the timezone
    tz = Column(String)  # wrong! https://stackoverflow.com/questions/30785635/

    properties = Column(JSONB)

    track_id = Column(Integer, ForeignKey(GPSTrack.id, ondelete="CASCADE"))
    track = relationship('GPSTrack', back_populates='points')

    @property
    def is_east(self):
        return self.longitude > 0

    @property
    def coords(self):
        if self.elevation is None:
            return (self.longitude, self.latitude)
        return (self.longitude, self.latitude, self.elevation)

    @property
    def lat_lon(self):
        # always between -180 and 180 longitude
        return [float(self.latitude), float(self.longitude + 180) % 360 - 180]

    def corrected_coords(self, east=True, include_elevation=False):
        # for tracks that cross the antimeridian or incidentally the meridian,
        # this helps leaflet.js figure out not to try to wrap the world
        longitude = self.longitude
        if east and self.longitude < 0:
            longitude += 360  # stay east
        if not east and self.longitude > 0:
            longitude -= 360  # stay west
        if self.elevation is None or not include_elevation:
            return (float(longitude), float(self.latitude))
        return (float(longitude), float(self.latitude), float(self.elevation))

    def set_timezone(self, tzinfo):
        """For some reason Postgres uses the opposite sign"""
        minutes = int(tzinfo.utcoffset(None).total_seconds() / 60)
        sign = '+' if minutes < 0 else '-'
        minutes = abs(minutes)
        self.tz = f"UTC{sign}{minutes // 60:02d}:{minutes % 60:02d}"

    @property
    def localtime(self):
        """Time in the local timezone"""
        match = re.match(r'UTC([+-])(\d+):(\d+)', self.tz or "")
        if not match:
            return self.time
        sign, hours, minutes = match.groups()
        sign = -1 if sign == '+' else 1
        offset = timedelta(minutes=sign * (int(hours) * 60 + int(minutes)))
        return self.time.astimezone(timezone(offset))

    def __str__(self):
        return f"<GPSPoint {self.time} {self.latitude}, {self.longitude}>"


class Categorization(Base):
    __tablename__ = 'categorization'

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)
    old_category = Column(String)
    old_name = Column(String)


def clone_model(model, **kwargs):
    """Clone an arbitrary sqlalchemy model object without its primary key values."""
    # Ensure the model’s data is loaded before copying.
    model.id

    table = model.__table__
    non_pk_columns = [k for k in table.columns.keys() if k not in table.primary_key]
    data = {c: getattr(model, c) for c in non_pk_columns}
    data.update(kwargs)

    clone = model.__class__(**data)
    return clone

def save_gpx(file, tracks):
    gpx = gpxpy.gpx.GPX()
    for t in tracks:
        g = t.as_gpxpy
        if isinstance(g, gpxpy.gpx.GPXWaypoint):
            gpx.waypoints.append(g)
        else:
            gpx.tracks.append(g)
    with open(file, "w") as fh:
        print(fh, gpx.to_xml())

if __name__ == '__main__':
    engine = sqlalchemy.create_engine(db_url(), echo=True)
    Base.metadata.create_all(engine)
