import json
import foursquare
import datetime
import gpxpy.gpx
from collections import defaultdict
import os.path
from secrets import foursquare_client_id, foursquare_client_secret
import re
from os import listdir

# redirect_uri registered on developer.foursquare.com
redirect_uri = 'https://wander.ingstar.com'

# directory to save monthly files in
gpx_dir = '/Users/aneel/Documents/Travel/Tracks/Foursquare Tracks'
gpx_file_pattern = 'Foursquare {month}.GPX'

def month_file(month):
    return os.path.join(gpx_dir, gpx_file_pattern.format(month=month))

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

        # Apply the returned access token to the client
        client.set_access_token(access_token)

        return client
    else:
        raise RuntimeError("Callback URL didn't include a code")

def complete_gpx_files():
    # find all of the months that we've already grabbed
    gpx_files = sorted([os.path.join(gpx_dir, f) for f in listdir(gpx_dir) if os.path.isfile(os.path.join(gpx_dir, f))])
    # we might have some new checkins in the most recent month, so remove it
    if gpx_files:
        gpx_files = gpx_files[:-1]
    return set(gpx_files)


def save_new_gpx_files(client, complete_gpx_files):
    by_month = defaultdict(list)
    venues_seen = {}

    checkins = client.users.all_checkins()
    for checkin in checkins:
        if checkin['type'] != 'checkin':
            continue
        dt = datetime.datetime.fromtimestamp(checkin['createdAt'])
        checkin['createdAtDatetime'] = dt
        month = dt.strftime("%Y-%m")
        if month not in by_month:
            print(f"found checkings for {month}")
        by_month[month].append(checkin)

    for month in sorted(by_month.keys()):
        checkins = by_month[month]
        print(f"{month} {len(checkins)}")
        if month_file(month) in complete_gpx_files:
            continue
        else:
            print(f"processing {month_file(month)}")

        gpx = gpxpy.gpx.GPX()

        for checkin in checkins:
            checkin_time = checkin['createdAtDatetime']
            if 'venue' in checkin:
                venue_id = checkin['venue']['id']
                venue_name = checkin['venue']['name']
                if venue_id not in venues_seen:
                    venues_seen[venue_id] = client.venues(venue_id)
                    print(f"{venue_id}: {venues_seen[venue_id].get('name')}")
                venue = venues_seen[venue_id]
                lat = venue.get('venue', {}).get('location', {}).get('lat')
                lng = venue.get('venue', {}).get('location', {}).get('lng')
            elif 'location' in checkin:
                venue_name = checkin['location']['name']
                lat = checkin['location']['lat']
                lng = checkin['location']['lng']
            else:
                print(checkin)
            print(f"{checkin_time.isoformat()} {venue_name}")

            if lat and lng:
                track = gpxpy.gpx.GPXTrack()
                track.name = f"{venue_name} {checkin_time.isoformat()}"
                segment = gpxpy.gpx.GPXTrackSegment()
                segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lng, time=checkin_time))
                track.segments.append(segment)
                gpx.tracks.append(track)
            else:
                print(json.dumps(venue, indent=2))

        with open(month_file(month), 'w') as gpx_file:
            print(gpx.to_xml(), file=gpx_file)

save_new_gpx_files(authenticated_client(), complete_gpx_files())