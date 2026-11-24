"""Unit tests for targeting.py.  Run:  python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import targeting as t  # noqa: E402


class ScanAngles(unittest.TestCase):
    def test_thirteen_steps_both_ends(self):
        a = t.scan_angles()
        self.assertEqual(len(a), 13)
        self.assertEqual((a[0], a[-1]), (3000, 1800))

    def test_ascending(self):
        self.assertEqual(t.scan_angles(1800, 3000)[-1], 3000)


class Filter(unittest.TestCase):
    def test_median_rejects_spikes(self):
        self.assertEqual(t.filter_reading(2000, [500, 8190, 501, 0, 499]), (2000, 500))

    def test_out_of_range_dropped(self):
        self.assertIsNone(t.filter_reading(2000, [8190] * 7))
        self.assertIsNone(t.filter_reading(2000, [10] * 7))

    def test_empty_samples(self):
        self.assertIsNone(t.filter_reading(2000, []))


class Clusters(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(t.find_clusters([]), [])

    def test_angle_gap_splits(self):
        c = t.find_clusters([(3000, 500), (2900, 500), (2500, 500)])
        self.assertEqual(len(c), 2)

    def test_depth_jump_splits_side_by_side_objects(self):
        r = [(2600, 400), (2500, 400), (2400, 900), (2300, 900)]
        c = t.find_clusters(r)
        self.assertEqual(len(c), 2)

    def test_order_independent(self):
        r = [(2000, 300), (2100, 300), (2200, 300)]
        self.assertEqual(t.find_clusters(r), t.find_clusters(list(reversed(r))))


class ChooseTarget(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(t.choose_target([]))

    def test_nearest_wins_and_centred(self):
        clusters = t.find_clusters(
            [(2900, 800), (2800, 800), (2300, 300), (2200, 300), (2100, 300)])
        self.assertEqual(t.choose_target(clusters), (2200, 300))

    def test_side_by_side_aims_at_near_object(self):
        r = [(2600, 400), (2500, 400), (2400, 900), (2300, 900)]
        self.assertEqual(t.choose_target(t.find_clusters(r)), (2550, 400))


class Degrees(unittest.TestCase):
    def test_range(self):
        self.assertAlmostEqual(t.us_to_degrees(3000), 45)
        self.assertAlmostEqual(t.us_to_degrees(1800), -45)
        self.assertAlmostEqual(t.us_to_degrees(2400), 0)


if __name__ == "__main__":
    unittest.main()
