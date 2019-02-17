import gpxpy.gpx
from geojson import Feature, FeatureCollection, MultiLineString, dumps
import argparse
import re

def convert_to_geojson(gpx):
    features = []
    for track in gpx.tracks:
        lines = []
        for segment in track.segments:
            lines.append([(p.longitude, p.latitude, p.elevation) for p in segment.points])
        features.append(Feature(geometry=MultiLineString(lines),
                                properties={'name': track.name,
                                            'description': track.description,
                                            'comment': track.comment}))
    return FeatureCollection(features)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='+', help="Path to GPX files to process")
    args = parser.parse_args()

    for file in args.input:
        with open(file, 'r') as gpx_file:
            print(f"Loading {file}")
            input_gpx = gpxpy.parse(gpx_file)

        outfile = re.sub(r'\.gpx$', '.json', file, flags=re.IGNORECASE)
        if outfile == file:
            raise ValueError(f"GPX file name should end with .gpx: {file}")
        output_geojson = convert_to_geojson(input_gpx)
        with open(outfile, 'w') as json_file:
            print(f"Writing {outfile}")
            print(dumps(output_geojson), file=json_file)
