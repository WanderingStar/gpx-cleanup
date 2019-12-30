import unittest

from geodb.model import GPSTrack, GPSPoint


class TestWrapping(unittest.TestCase):

    @staticmethod
    def lat_lons_to_polyline(lat_lons):
        track = GPSTrack()
        track.points = [GPSPoint(latitude=lat, longitude=lon) for lat, lon in lat_lons]
        return track.as_polyline()

    def test_no_cross(self):
        lat_lons = [[20., -10.], [-20., 10.]]
        self.assertEqual([[[20., -10.], [-20., 10.]]],
                         TestWrapping.lat_lons_to_polyline(lat_lons).locations)

    def test_simple(self):
        lat_lons = [[20., -170.], [10., -175.], [-10., 175.], [-20., 170.]]
        self.assertEqual([[[20., -170.], [10., -175.], [0., -180.]],
                          [[0., 180.], [-10., 175.], [-20., 170.]]],
                         TestWrapping.lat_lons_to_polyline(lat_lons).locations)

    def test_asymmetric(self):
        lat_lons = [[20., -170.], [10., -175.], [-5., 170.]]
        self.assertEqual([[[20., -170.], [10., -175.], [5., -180.]],
                          [[5., 180.], [-5., 170.]]],
                         TestWrapping.lat_lons_to_polyline(lat_lons).locations)

    def test_double_cross(self):
        lat_lons = [[20., -170.], [10., -175.], [-10., 175.], [-20., -175.]]
        self.assertEqual([[[20., -170.], [10., -175.], [0., -180.]],
                          [[0., 180.], [-10., 175.], [-15., 180.]],
                          [[-15., -180.], [-20., -175.]]],
                         TestWrapping.lat_lons_to_polyline(lat_lons).locations)


if __name__ == '__main__':
    unittest.main()
