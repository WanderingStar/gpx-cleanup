import json
import os

import sqlalchemy
from geojson import Feature, MultiLineString, Point
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import decimal

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

    points = relationship('GPSPoint', order_by='GPSPoint.time', back_populates='track')

    @property
    def as_geojson_feature(self):
        props = dict(self.properties)
        props.update({
            'name': self.name,
            'comment': self.comment,
            'description': self.description,
            'source': self.source,
            'type': self.type
        })
        props = {k: v for k, v in props.items() if v is not None}
        if len(self.points) == 1:
            p = self.points[0]
            return Feature(geometry=Point(p.coords),
                           properties=props)

        return Feature(
            geometry=MultiLineString([p.coords for p in self.points]),
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
    def coords(self):
        if self.elevation is None:
            return (self.longitude, self.latitude)
        return (self.longitude, self.latitude, self.elevation)


def postgres_timezone(tzinfo):
    """For some reason Postgres uses the opposite sign"""
    minutes = int(tzinfo.utcoffset(None).total_seconds() / 60)
    sign = '+' if minutes < 0 else '-'
    minutes = abs(minutes)
    return f"UTC{sign}{minutes // 60:02d}:{minutes % 60:02d}"


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


if __name__ == '__main__':
    engine = sqlalchemy.create_engine(db_url(), echo=True)
    Base.metadata.create_all(engine)
