import gpxpy
import gpxpy.gpx
from intervaltree import IntervalTree
import datetime
import argparse
import re
from collections import Counter

pattern_labels = [
    ("Active Log", "Zumo"),
    ("Aneel Nazareth", "inReach")
]

def matching_labels(string):
    for pattern, label in pattern_labels:
        if re.search(pattern, string):
            yield label

def merge_track_segments_within_interval(segments, start, end):
    print(f"merging {len(segments)} segments\n in {start}, {end} ({(end - start).total_seconds()}s)")
    for s in segments:
        tbs = s.get_time_bounds().start_time
        tbe = s.get_time_bounds().end_time
        sec = (tbe - tbs).total_seconds()
        print(f"    {tbs}, {tbe} ({sec}s): {s.get_points_no()}")
    seg_points = []
    seg_extensions = []
    for s in segments:
        seg_points += s.points
        seg_extensions += s.extensions
    in_interval = [p for p in seg_points if p.time >= start and p.time <= end]
    print(f"    total points {len(seg_points)} -> {len(in_interval)}")
    merged = gpxpy.gpx.GPXTrackSegment(points=sorted(in_interval, key=lambda p: p.time))
    merged.extensions = list(set(seg_extensions))
    print(f"    extensions: {merged.extensions}")
    return merged

def gpx_merge_intersect(input_gpx):
    """
    Given an GPX file containing multiple overlapping tracks, merge the parts
    that overlap and create separate tracks for the parts that only partially
    overlap.
    """
    intervals = IntervalTree()

    all_points = set()

    for track in input_gpx.tracks:
        for segment in track.segments:
            bounds = segment.get_time_bounds()
            start = bounds.start_time.timestamp()
            end = bounds.end_time.timestamp()
            if start == end:
                end = end + 1
            print(f"Found track {track.name}")
            segment.extensions.append(f"OriginalName:{track.name}")
            intervals[start:end] = [segment]
            all_points.update(set([p.time for p in segment.points]))

    n_original = len(intervals)
    intervals.split_overlaps()
    for i in intervals:
        print(i)
    n_split = len(intervals)
    intervals.merge_equals(data_reducer=lambda a, b: a + b)
    n_merged = len(intervals)
    print(f"Split {n_original} intervals into {n_split} merged into {n_merged}")

    merged_points = set()

    output_gpx = input_gpx.clone()
    output_gpx.tracks = []

    for i in sorted(intervals):
        print(i)
        start = datetime.datetime.fromtimestamp(i.begin)
        end = datetime.datetime.fromtimestamp(i.end)
        segments = i.data
        merged = merge_track_segments_within_interval(segments, start, end)
        merged_points.update(set([p.time for p in merged.points]))

        original_names = []
        labels = Counter()
        custom_names = []  # names that didn't match the label patterns
        for ext in merged.extensions:
            match = re.match("OriginalName:(.*)", ext)
            if match:
                original_name = match.group(1)
                original_names.append(original_name)
                matching = list(matching_labels(original_name))
                if not matching:
                    print(f"custom name: {original_name}")
                    custom_names.append(original_name)
                else:
                    labels.update(matching)
        merged.extensions = [e for e in merged.extensions if not re.match("OriginalName:(.*)", e)]
        print(f"remaining extensions: {merged.extensions}")

        track = gpxpy.gpx.GPXTrack()
        track.segments.append(merged)

        track.name = " ".join(
            custom_names + [f"{k}: {v}" for k, v in labels.most_common()]
        )
        track.description = "\n".join(sorted(original_names))
        output_gpx.tracks.append(track)

    print(f"final tracks: {len(output_gpx.tracks)}")
    # make sure all of the points in the input made it through to one of the merged segments
    print(f"all: {len(all_points)}, merged: {len(merged_points)}")
    print(f"all points appear in merge: {all_points == merged_points}")

    return output_gpx


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to GPX file to process")
    parser.add_argument("output", help="Path to write processed GPX file")
    args = parser.parse_args()

    with open(args.input, 'r') as gpx_file:
        print(f"Loading {args.input}")
        input_gpx = gpxpy.parse(gpx_file)

    output_gpx = gpx_merge_intersect(input_gpx)
    with open(args.output, 'w') as gpx_file:
        print(output_gpx.to_xml(), file=gpx_file)
