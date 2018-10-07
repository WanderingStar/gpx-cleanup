import json
import foursquare
import datetime
import gpxpy.gpx
from collections import defaultdict
import os.path
from secrets import foursquare_client_id, foursquare_client_secret

with open('/Users/aneel/Documents/Travel/Tracks/Foursquare data_export_6620/checkins.json') as f:
    checkins = json.load(f)

client = foursquare.Foursquare(client_id=foursquare_client_id,
                               client_secret=foursquare_client_secret)

by_month = defaultdict(list)
venues_seen = {}

for checkin in checkins['items']:
    if checkin['type'] != 'checkin':
        continue
    dt = datetime.datetime.fromtimestamp(checkin['createdAt'])
    checkin['createdAtDatetime'] = dt
    month = dt.strftime("%Y-%m")
    by_month[month].append(checkin)

for month in sorted(by_month.keys()):
    checkins = by_month[month]
    print(f"{month} {len(checkins)}")
    if os.path.exists(f"/Users/aneel/Downloads/Foursquare {month}.GPX"):
        continue

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

    with open(f"/Users/aneel/Downloads/Foursquare {month}.GPX", 'w') as gpx_file:
        print(gpx.to_xml(), file=gpx_file)
