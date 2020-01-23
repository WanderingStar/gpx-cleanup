import argparse
from datetime import timedelta, timezone
import dateutil
import os.path
from collections import Counter

import json
import gzip
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from geodb.model import GPSPoint, GPSTrack, db_url

def load_locokit_file(session, filename):
    if filename.endswith('.gz'):
        with gzip.GzipFile(filename, 'r') as f:
            data = json.loads(f.read().decode('utf-8'))
    else:
        with open(filename, 'r') as f:
            data = json.load(f)
    for ti in data['timelineItems']:
        t = GPSTrack(source='Arc', filename=os.path.basename(filename))
        t.name = ti.get('place', {}).get('name')
        t.type = ti.get('activityType')
        for s in ti.get('samples', []):
            l = s.get('location')
            if l:
                p = GPSPoint(latitude=l['latitude'], longitude=l['longitude'],
                             elevation=l['altitude'],
                             time=dateutil.parser.parse(l['timestamp']))
                p.set_timezone(timezone(timedelta(seconds=s['secondsFromGMT'])))
                t.points.append(p)
        print(f"{t.name} {t.type}: {len(t.points)}")
        session.add(t)
        session.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='+', help="Path to GPX files to process")
    args = parser.parse_args()

    engine = sqlalchemy.create_engine(db_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    for f in args.input:
        print(f)
        load_locokit_file(session, f)
