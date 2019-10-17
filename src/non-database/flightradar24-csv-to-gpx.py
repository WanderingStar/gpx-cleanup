import csv
import datetime
import sys

import gpxpy.gpx
import os.path

def flightradar24_csv_to_gpx(path):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    track.name = os.path.basename(path)
    segment = gpxpy.gpx.GPXTrackSegment()
    with open(path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            lat, lng = row['Position'].split(',')
            utc = datetime.datetime.fromtimestamp(int(row['Timestamp']))
            segment.points.append(gpxpy.gpx.GPXTrackPoint(float(lat), float(lng), time=utc))
    track.segments.append(segment)
    gpx.tracks.append(track)
    return gpx

if __name__ == '__main__':
    path = sys.argv[1]
    gpx = flightradar24_csv_to_gpx(path)
    print(gpx.to_xml())
