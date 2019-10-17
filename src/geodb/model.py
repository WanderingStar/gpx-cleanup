import os
import re
import sqlalchemy
from datetime import timezone, timedelta
from geojson import Feature, LineString, Point
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey


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

    properties = Column(JSONB)
    raw = Column(JSONB)

    points = relationship('GPSPoint', order_by='GPSPoint.time', back_populates='track')

    @property
    def start_localtime(self):
        if not self.points:
            return None
        return self.points[0].localtime

    @property
    def end_localtime(self):
        if not self.points:
            return None
        return self.points[-1].localtime

    @property
    def is_east(self):
        if not self.points:
            return None
        return self.points[0].is_east

    def as_geojson_feature(self, east):
        props = dict(self.properties)
        props.update({
            'track_id': self.id,
            'name': self.name,
            'comment': self.comment,
            'description': self.description,
            'source': self.source,
            'type': self.type,
            'start': str(self.start_localtime),
            'end': str(self.end_localtime),
        })
        props = {k: v for k, v in props.items() if v is not None}
        if len(self.points) == 1:
            p = self.points[0]
            return Feature(geometry=Point(p.corrected_coords(east)),
                           properties=props)

        east = east if east is not None else self.is_east
        return Feature(
            geometry=LineString([p.corrected_coords(east) for p in self.points]),
            properties=props)


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

    def corrected_coords(self, east=True):
        # for tracks that cross the antimeridian or incidentally the meridian,
        # this helps leaflet.js figure out not to try to wrap the world
        longitude = self.longitude
        if east and self.longitude < 0:
            longitude += 360  # stay east
        if not east and self.longitude > 0:
            longitude -= 360  # stay west
        if self.elevation is None:
            return (longitude, self.latitude)
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


class Categorization(Base):
    __tablename__ = 'categorization'

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)
    old_category = Column(String)
    old_name = Column(String)


if __name__ == '__main__':
    engine = sqlalchemy.create_engine(db_url(), echo=True)
    Base.metadata.create_all(engine)
