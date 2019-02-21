import argparse
import os
from collections import defaultdict

import gpxpy.gpx
import requests
import dateutil.parser
import re

from secrets import azure_key

iso_pattern = r'\d\d\d\d-\d\d-\d\d[T ]\d\d:\d\d:\d\d([+-]\d\d:?\d\d|Z)?\s*'

def first_point_with_time(gpx_track):
    for segment in gpx_track.segments:
        for point in segment.points:
            if point.time:
                return point


def localtime_for_point(gpx_point):
    params = {
        "subscription-key": azure_key,
        "api-version": "1.0",
        "options": "all",
        "query": f"{gpx_point.latitude},{gpx_point.longitude}",
        "timeStamp": gpx_point.time.isoformat() + "Z"
    }
    r = requests.get("https://atlas.microsoft.com/timezone/byCoordinates/json", params=params)
    r.raise_for_status()
    return dateutil.parser.parse(r.json()["TimeZones"][0]["ReferenceTime"]["WallTime"])


def organize_by_local_day(input_gpx):
    """Returns a dict of string date -> [(time, track)]"""

    tracks_by_date = defaultdict(list)
    for track in input_gpx.tracks:
        date = "Unknown"
        time = None
        old_name = track.name
        try:
            point = first_point_with_time(track)
            time = point.time  # UTC!
            local = localtime_for_point(point)
            date = local.date().isoformat()
            # strip out any lingering datetimes introduced by other things
            # and prepend the local time
            track.name = local.time().isoformat() + " " + re.sub(iso_pattern, '', old_name)
        finally:
            print(f"Added track at {time} UTC = {local.isoformat()} local: {old_name}")
            tracks_by_date[date].append((time, track))
    return tracks_by_date


def sort_tracks_into_gpx(tracks_by_date):
    gpx_by_date = {}
    for date, time_tracks in sorted(tracks_by_date.items(), key=lambda t: t[0]):
        output_gpx = gpxpy.gpx.GPX()
        output_gpx.tracks = []
        sorted_time_tracks = sorted(time_tracks, key=lambda t: t[0])
        print(f"Sorting {date}\n" + "\n".join([f"  {ti} UTC: {tr.name}" for ti,tr in sorted_time_tracks]))
        for time, track in sorted_time_tracks:
            track.extensions = None  # TODO gpxpy doesn't deal with garmin extensions properly
            track.number = len(output_gpx.tracks) + 1
            output_gpx.tracks.append(track)
        gpx_by_date[date] = output_gpx

    return gpx_by_date


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='+', help="Path to GPX file to process")
    parser.add_argument("output_dir", help="Path to directory to put resulting files in")
    args = parser.parse_args()

    dir = os.path.abspath(args.output_dir)
    os.makedirs(dir, exist_ok=True)

    all_tracks_by_date = defaultdict(list)
    for input_path in args.input:
        with open(input_path, "r") as gpx_file:
            print(f"Loading {input_path}")
            input_gpx = gpxpy.parse(gpx_file)
            for date, tracks in organize_by_local_day(input_gpx).items():
                all_tracks_by_date[date].extend(tracks)

    gpx_by_date = sort_tracks_into_gpx(all_tracks_by_date)
    for date, gpx in gpx_by_date.items():
        output_path = os.path.join(dir, f"{date}.gpx")
        with open(output_path, "w") as out_file:
            print(gpx.to_xml(), file=out_file)
