#import argparse
import bisect
import csv
import datetime
from collections import namedtuple

import dateutil.parser
import gpxpy.gpx


def segment_containing(gpx, dive_start, dive_end):
    for track in gpx.tracks:
        for segment in track.segments:
            (seg_start, seg_end) = segment.get_time_bounds()
            if seg_start < dive_start and seg_end > dive_end:
                return segment
    return None

def named_track(points, name, desc):
    track = gpxpy.gpx.GPXTrack()
    track.name = name
    track.description = desc
    track.segments = [gpxpy.gpx.GPXTrackSegment()]
    track.segments[0].points = points
    return track

def divide_segment(segment, dive_start, dive_end, dive_name):
    points = sorted(segment.points, key=lambda p: p.time)
    times = [p.time for p in points]
    start = bisect.bisect_right(times, dive_start)
    end = bisect.bisect_left(times, dive_end)

    # What the skiff was doing before, during, and after the dive
    before = named_track(points[0:start], f"To {dive_name}", "Skiff")
    during = named_track(points[start:end], f"During {dive_name}", "Skiff")
    after = named_track(points[end:], f"From {dive_name}", "Skiff")

    # The dive is just two points, based on where the skiff was at the time
    dive = named_track([points[start], points[end]], dive_name, "Dive")

    return [before, during, after, dive]


if __name__ == '__main__':
    #parser = argparse.ArgumentParser()
    #parser.add_argument("input", help="Path to GPX file to process")
    #args = parser.parse_args()

    input_file = "/Users/aneel/Documents/Travel/201812 Palau/All-overlap-trimmed-overlap.gpx"
    output_file = "/Users/aneel/Documents/Travel/201812 Palau/Dives.gpx"
    csv_file = "/Users/aneel/Documents/Travel/201812 Palau/Dives.csv"
    timezone = "+09:00"  # force Palau time

    with open(input_file, "r") as gpx_file:
        print(f"Loading {input_file}")
        input_gpx = gpxpy.parse(gpx_file)

    ExplodedPoint = namedtuple('ExplodedPoint', ['time', 'point', 'segment', 'track'])

    exploded_points = sorted([ExplodedPoint(point.time, point, segment, track)
                              for track in input_gpx.tracks
                              for segment in track.segments
                              for point in segment.points
                              if point.time], key=lambda p: p.time)
    times = [p.time for p in exploded_points]

    output_gpx = gpxpy.gpx.GPX()
    output_gpx.tracks = []

    Dive = namedtuple('Dive', ['name', 'start', 'end'])
    dives = []

    with open(csv_file) as fh:
        csv_reader = csv.DictReader(fh)

        for row in csv_reader:
            name = row['Site Name']
            start_date = dateutil.parser.parse(row['Date'] + '+09:00')  # force Palau time
            utc_start_date = start_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            utc_end_date = utc_start_date + datetime.timedelta(seconds=int(row['Total Duration']))
            dives.append(Dive(name, utc_start_date, utc_end_date))

    for dive in dives:
        start_index = bisect.bisect_right(times, dive.start)
        end_index = bisect.bisect_left(times, dive.end)

        if start_index != end_index:
            # the segment containing the start is the To Dive segment
            segment = exploded_points[start_index].segment
            points = [p for p in segment.points if p.time < dive.start]
            if points:
                output_gpx.tracks.append(named_track(points, f'{points[0].time} To {dive.name}', 'Skiff'))
            else:
                print(f"No points in To {dive.name}")

            # all points between the start and end are the during segment: what the skiff did during the dive
            points = [p.point for p in exploded_points[start_index:end_index]]
            output_gpx.tracks.append(named_track(points, f'{points[0].time} During {dive.name}', 'Skiff'))

            # the segment containing the end is the From Dive segment
            segment = exploded_points[end_index].segment
            points = [p for p in segment.points if p.time > dive.end]
            if points:
                output_gpx.tracks.append(named_track(points, f'{points[0].time} From {dive.name}', 'Skiff'))
            else:
                print(f"No points in From {dive.name}")

        # since the GPS isn't on the dive, the dive track is just the start and end points
        points = [exploded_points[start_index].point, exploded_points[end_index].point]
        output_gpx.tracks.append(named_track(points, f'{points[0].time} {dive.name}', 'Dive'))

    with open(output_file, "w") as out_file:
        print(output_gpx.to_xml(), file=out_file)

