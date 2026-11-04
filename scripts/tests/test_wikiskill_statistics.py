import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wikiskill_statistics import exact_bounds, paired_quality, resource_ratio, ALPHA_BOUND


class StatisticsTest(unittest.TestCase):
    def test_exact_zero_and_all_success_boundaries(self):
        for n in (16,32,48):
            low,high=exact_bounds(0,n)
            self.assertEqual(low,0)
            self.assertAlmostEqual(high,1-ALPHA_BOUND**(1/n),places=10)
            low,high=exact_bounds(n,n)
            self.assertEqual(high,1)
            self.assertAlmostEqual(low,ALPHA_BOUND**(1/n),places=10)

    def test_paired_reversibility_and_futility(self):
        a=[True,False]*24
        b=[False,True]*24
        ab=paired_quality(a,b)
        ba=paired_quality(b,a)
        self.assertAlmostEqual(ab['lower'],-ba['upper'])
        self.assertEqual(ab['wins'],24)
        same=paired_quality([True]*48,[True]*48)
        self.assertTrue(same['practical_gain_futile'])
        self.assertLess(same['upper'],.15)
        self.assertFalse(paired_quality([True]*16,[True]*16)['practical_gain_futile'])
        for n in (16,32,48):
            all_win=paired_quality([True]*n,[False]*n)
            self.assertGreaterEqual(all_win['lower'],-1)
            self.assertLessEqual(all_win['upper'],1)

    def test_resource_ratio_is_paired_and_reproducible(self):
        ratio=resource_ratio([1,2,3],[2,4,6],draws=100)
        self.assertAlmostEqual(ratio['geometric_ratio'],.5)
        self.assertAlmostEqual(ratio['lower'],.5)
        self.assertAlmostEqual(ratio['upper'],.5)
        self.assertFalse(resource_ratio([0,1],[1,1],draws=100)['estimable'])
