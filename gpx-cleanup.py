import gpxpy
import gpxpy.gpx
from intervaltree import IntervalTree
import datetime

# Parsing an existing file:
# -------------------------

with open('/Users/aneel/Downloads/Iceland raw.GPX', 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)

intervals = IntervalTree()

all_points = set()

for track in gpx.tracks:
    for segment in track.segments:
        bounds = segment.get_time_bounds()
        start = bounds.start_time.timestamp()
        end = bounds.end_time.timestamp()
        driving = "Active Log" in track.name
        segment.extensions.append(track.name)
        if start != end:
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

merged_points = set()

gpx = gpxpy.gpx.GPX()

for i in sorted(intervals):
    print(i)
    start = datetime.datetime.fromtimestamp(i.begin)
    end = datetime.datetime.fromtimestamp(i.end)
    segments = i.data
    merged = merge_track_segments_within_interval(segments, start, end)
    merged_points.update(set([p.time for p in merged.points]))
    zumo = len([e for e in merged.extensions if "Active Log" in e])
    inreach = len(merged.extensions) - zumo
    merged.extensions = []
    track = gpxpy.gpx.GPXTrack()
    track.segments.append(merged)
    track.name = f"{start} Zumo {zumo} inReach {inreach}"
    track.description = "\n".join(sorted(merged.extensions))
    gpx.tracks.append(track)

print(f"final tracks: {len(gpx.tracks)}")
# make sure all of the points in the input made it through to one of the merged segments
print(f"all: {len(all_points)}, merged: {len(merged_points)}")
print(f"all points appear in merge: {all_points == merged_points}")

#    print(f"{track.get_time_bounds().start_time}\t{track.get_time_bounds().end_time}\t{track.get_points_no()}\t{track.length_2d()}\t{track.name}")
#    for segment in track.segments:
#        for point in segment.points:
#            print('Point at ({0},{1}) -> {2}'.format(point.latitude, point.longitude, point.elevation))

with open('/Users/aneel/Downloads/Iceland cleaned.GPX', 'w') as gpx_file:
    print(gpx.to_xml(), file=gpx_file)
