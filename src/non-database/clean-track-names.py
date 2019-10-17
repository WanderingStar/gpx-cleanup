import gpxpy.gpx
import argparse
import re

def clean_track_names(gpx):
    for track in gpx.tracks:
        old = track.name
        # remove inReach track count
        track.name = re.sub(r'\s*inReach: \d+', '', track.name)
        # remove Zumo track count
        track.name = re.sub(r'\s*Zumo: \d+', '', track.name)
        # Remove repetition when During dive Skiff trip gets merged with Dive track
        track.name = re.sub(r'During (.+) \1', r'During \1', track.name)
        track.name = re.sub(r'(.+) During \1', r'During \1', track.name)
        if track.name != old:
            print(f'{old} -> {track.name}')

        if re.match(r'\d+:\d+:\d+ Zumo: \d+$', old):
            track.description = 'Car'
            print(f'{track.name} == {track.description}')
        elif re.search(r'(To |From |During )', track.name):
            track.description = 'Skiff'
            print(f'{track.name} == {track.description}')
    return gpx

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='+', help="Path to GPX files to process")
    args = parser.parse_args()

    for file in args.input:
        with open(file, 'r') as gpx_file:
            print(f"Loading {file}")
            input_gpx = gpxpy.parse(gpx_file)

        output_gpx = clean_track_names(input_gpx)
        with open(file, 'w') as gpx_file:
            print(output_gpx.to_xml(), file=gpx_file)
