import datetime
import re

import foursquare
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from geodb.model import GPSPoint, db_url, GPSTrack
from secrets import foursquare_client_id, foursquare_client_secret

# redirect_uri registered on developer.foursquare.com
redirect_uri = 'https://wander.ingstar.com'


def authenticated_client():
    client = foursquare.Foursquare(client_id=foursquare_client_id,
                                   client_secret=foursquare_client_secret,
                                   redirect_uri=redirect_uri)

    auth_uri = client.oauth.auth_url()
    print(f"Please go to {auth_uri}")
    response = input("Paste the full callback URL: ")
    match = re.search(r'code=(\w+)', response)
    if match:
        code = match.group(1)
        access_token = client.oauth.get_token(code)
        print(access_token)

        # Apply the returned access token to the client
        client.set_access_token(access_token)

        return client
    else:
        client.set_access_token(response)
        return client


def load_4sq_checkin(session, checkin):
    tz = datetime.timezone(datetime.timedelta(minutes=checkin['timeZoneOffset']))
    dt = datetime.datetime.fromtimestamp(checkin['createdAt'], tz)
    # utc_dt = dt.astimezone(datetime.timezone.utc)

    if 'venue' not in checkin:
        return None

    venue = checkin['venue']
    primary_categories = [c for c in venue.get('categories', []) if c.get('primary', False)]
    primary_category = primary_categories[0]['name'] if primary_categories else None

    gps_track = GPSTrack(name=venue["name"], description=primary_category,
                         source="4sq", type="Waypoint")
    gps_track.properties = {
        'checkin_id': checkin['id'],
        'venue_id': venue['id'],
        'timezone': str(tz),
    }
    gps_track.raw = checkin
    gps_point = GPSPoint(latitude=venue['location']['lat'],
                         longitude=venue['location']['lng'],
                         time=dt,
                         track=gps_track)
    gps_point.set_timezone(tz)
    gps_point.properties = {
        'localtime': dt.isoformat(),
    }

    session.add(gps_track)
    session.add(gps_point)
    return gps_track


def load_4sq():
    engine = sqlalchemy.create_engine(db_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = authenticated_client()
    checkins = client.users.all_checkins()
    m = 1
    for i, checkin in enumerate(checkins):
        if checkin['type'] != 'checkin':
            continue
        # checkin with this ID is already in the DB
        if (session
                .query(GPSTrack)
                .filter(GPSTrack.properties['checkin_id'].astext == checkin['id'])
                .count()) > 0:
            # continue
            pass
        gps_track = load_4sq_checkin(session, checkin)
        if gps_track:
            session.commit()
            if i % m == 0:
                m *= 2
                print(f"{i}\t{gps_track.points[0].properties['localtime']}\t{gps_track.name}")


if __name__ == '__main__':
    load_4sq()
