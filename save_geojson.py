from collections import defaultdict

import sqlalchemy
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from geojson import FeatureCollection
import simplejson as json

from model import GPSPoint, GPSTrack, db_url, DecimalEncoder

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument("input", nargs='+', help="Path to GPX files to process")
    # args = parser.parse_args()

    engine = sqlalchemy.create_engine(db_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # for track in session.query(GPSTrack).filter(
    #    func.timezone(GPSTrack.points[0].tz, GPSTrack.points[0].time) < '2018-12-25'):
    #    print(track.name)

    features = []
    for track_id, time in (
            session.query(GPSPoint.track_id, func.min(GPSPoint.time).label('time'))
                    .filter(func.date(func.timezone(GPSPoint.tz, GPSPoint.time)) == '2018-12-26')
                    .group_by(GPSPoint.track_id)
                    .order_by('time')
    ):
        features.append(session.query(GPSTrack).get(track_id).as_geojson_feature)
        print(session.query(GPSTrack).get(track_id).name)
    collection = FeatureCollection(features)

    outfile = "/Users/aneel/Downloads/2018-12-26.json"
    with open(outfile, 'w') as json_file:
        json.dump(collection, json_file, use_decimal=True)
