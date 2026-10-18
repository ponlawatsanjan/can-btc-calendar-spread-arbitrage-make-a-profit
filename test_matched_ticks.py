from pathlib import Path
import tempfile
import unittest

from plot_matched_ticks import query_matched, query_days, pairs_from


class MatchTests(unittest.TestCase):
    def test_latest_past_strict_boundary_ties_and_far_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            near=Path(directory)/'near.csv';far=Path(directory)/'far.csv'
            near.write_text('1,100,1,100,10000,true\n2,101,1,101,10999,true\n3,102,1,102,11000,true\n4,103,1,103,11100,true\n5,104,1,104,11100,true\n')
            far.write_text('10,110,1,110,10000,true\n11,111,1,111,10000,true\n12,112,1,112,11001,true\n')
            result=query_matched([near],[far],10000,12000,100)
            self.assertEqual(result['near_ticks_examined'],5)
            self.assertEqual(result['unmatched_near_ticks'],1)
            rows=result['ticks']
            self.assertEqual([r[3] for r in rows],['1','2','4','5'])
            self.assertEqual([r[8] for r in rows],['11','11','12','12'])
            self.assertEqual([r[9] for r in rows],[0,999,99,99])
            self.assertTrue(all(0<=r[0]-r[7]<1000 for r in rows))
            self.assertEqual(rows[0][1],11)
            self.assertEqual(rows[0][10],rows[1][10])
            self.assertNotEqual(rows[1][10],rows[2][10])
            self.assertEqual(rows[2][10],rows[3][10])

    def test_carry_in_and_sampling_after_matching(self):
        with tempfile.TemporaryDirectory() as directory:
            near=Path(directory)/'near.csv';far=Path(directory)/'far.csv'
            near.write_text(''.join(f'{i},{100+i},1,100,{10000+i},true\n' for i in range(40)))
            far.write_text('1,150,1,150,9999,true\n')
            result=query_matched([near],[far],10000,11000,8)
            self.assertEqual(result['raw_rows_in_window'],40)
            self.assertTrue(result['sampled'])
            self.assertTrue(all(r[7]==9999 for r in result['ticks']))

    def test_all_overlapping_same_underlying_pairs(self):
        entries=[(0,Path('example.csv'))]
        result=pairs_from({'BTCUSDT_260925':entries,'BTCUSDT_261225':entries,'BTCUSDT_270326':entries,'BTCUSDT':entries,'ETHUSDT_261225':entries})
        self.assertEqual(len(result),3)
        self.assertIn('BTCUSDT_260925 / BTCUSDT_270326',result)
        self.assertFalse(pairs_from({'BTCUSDT_260925':[(0,Path('a'))],'BTCUSDT_270326':[(864000000,Path('b'))]}))

    def test_daily_chunking_retains_global_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            near=Path(directory)/'near.csv';far=Path(directory)/'far.csv'
            near.write_text('1,100,1,100,10000,true\n2,101,1,101,10999,true\n')
            far.write_text('11,111,1,111,10000,true\n')
            result=query_days([(0,near)],[(0,far)],10000,12000,100)
            self.assertEqual(result['raw_rows_in_window'],2)
            self.assertEqual([r[1] for r in result['ticks']],[11,10])

    def test_day_boundary_preserves_real_continuity_but_breaks_quiet_intervals(self):
        day=86400000
        with tempfile.TemporaryDirectory() as directory:
            a=Path(directory)/'near-a.csv';b=Path(directory)/'near-b.csv'
            x=Path(directory)/'far-a.csv';y=Path(directory)/'far-b.csv'
            a.write_text(f'1,100,1,100,{day-500},true\n')
            b.write_text(f'2,101,1,101,{day+100},true\n3,102,1,102,{day+2100},true\n')
            x.write_text(f'11,110,1,110,{day-600},true\n')
            y.write_text(f'12,111,1,111,{day},true\n13,112,1,112,{day+2000},true\n')
            result=query_days([(0,a),(day,b)],[(0,x),(day,y)],day-1000,day+3000,100)
            rows=result['ticks']
            self.assertEqual(len(rows),3)
            self.assertEqual(rows[0][10],rows[1][10])
            self.assertNotEqual(rows[1][10],rows[2][10])



if __name__=='__main__':
    unittest.main()
