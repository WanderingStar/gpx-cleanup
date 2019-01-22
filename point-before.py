#import argparse
import csv
import datetime

import dateutil.parser
import gpxpy.gpx

def point_before(gpx, utc_dt):
    last_point = None
    for track in gpx.tracks:
        for segment in track.segments:
            (start, end) = segment.get_time_bounds()
            if start < utc_dt and utc_dt < end:
                last_point = segment.points[-1]
                for point in segment.points:
                    if point.time and point.time < utc_dt:
                        last_point = point
                return last_point
            else:
                if end < utc_dt and (last_point is None or last_point.time < end):
                    last_point = segment.points[-1]
    return last_point


if __name__ == '__main__':
    #parser = argparse.ArgumentParser()
    #parser.add_argument("input", help="Path to GPX file to process")
    #args = parser.parse_args()

    input_file = "/Users/aneel/Documents/Travel/201812 Palau/All-overlap-trimmed-overlap.gpx"
    output_file = "/Users/aneel/Documents/Travel/201812 Palau/Dives.gpx"
    csv_file = "/Users/aneel/Documents/Travel/201812 Palau/Dives.csv"

    with open(input_file, "r") as gpx_file:
        print(f"Loading {input_file}")
        input_gpx = gpxpy.parse(gpx_file)

    output_gpx = gpxpy.gpx.GPX()
    output_gpx.tracks = []

    with open(csv_file) as fh:
        csv_reader = csv.DictReader(fh)

        for row in csv_reader:
            name = row['Site Name']
            date = dateutil.parser.parse(row['Date'] + '+09:00').astimezone(datetime.timezone.utc).replace(tzinfo=None)
            last_point = point_before(input_gpx, date)
            track = gpxpy.gpx.GPXTrack()
            track.name = name
            segment = gpxpy.gpx.GPXTrackSegment()
            segment.points = [last_point]
            track.segments = [segment]
            output_gpx.tracks.append(track)
            print("\t".join([str(o) for o in [
                date.isoformat(),
                last_point.time.isoformat(),
                date - last_point.time,
                last_point.latitude,
                last_point.longitude,
                name,]]))

    with open(output_file, "w") as out_file:
        print(output_gpx.to_xml(), file=out_file)

