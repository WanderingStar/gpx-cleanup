import gpxpy.gpx
import argparse
import re
from collections import defaultdict
from datetime import timedelta

class Summary:
    def __init__(self):
        self.tracks = 0
        self.points = 0
        self.distance = 0
        self.moving_time = 0
        self.stopped_time = 0
        self.max_speed = 0

    def add_track(self, track):
        track.reduce_points(min_distance=10)
        self.tracks += 1
        self.points += track.get_points_no()
        moving_data = track.get_moving_data()
        self.distance += moving_data.moving_distance
        self.moving_time += moving_data.moving_time
        self.stopped_time += moving_data.stopped_time
        self.max_speed = max(self.max_speed, moving_data.max_speed)

    def table(self):
        return f"""Tracks\t{self.tracks}
Points\t{self.points}
Distance\t{self.distance:.2f} m\t{self.distance * 0.0006213712:.2f} mi
Moving Time\t{timedelta(seconds=self.moving_time)}
Stopped Time\t{timedelta(seconds=self.stopped_time)}
Max Speed\t{self.max_speed:.2f} m/s\t{self.max_speed * 0.0006213712 * 3600:.2f} mph
"""


def summarize(gpx, by_desc):
    for track in gpx.tracks:
        if not track.description:
            print(f"Track {track.name} has no description")
            continue
        summary = by_desc[track.description]
        summary.add_track(track)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='+', help="Path to GPX files to process")
    args = parser.parse_args()

    by_desc = defaultdict(Summary)

    for file in args.input:
        with open(file, 'r') as gpx_file:
            print(f"Loading {file}")
            input_gpx = gpxpy.parse(gpx_file)
            summarize(input_gpx, by_desc)

    for desc, summary in sorted(by_desc.items()):
        print(desc)
        print(summary.table())