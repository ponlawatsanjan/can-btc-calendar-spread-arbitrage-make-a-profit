from datetime import date
from pathlib import Path
import tempfile
import unittest

from plot_raw_ticks import inventory, midnight, query_contract


class RawViewerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.file = Path(self.directory.name) / 'BTCUSDT_260925-trades-2026-09-01.csv'
        self.start = midnight(date(2026, 9, 1))

    def test_exact_ticks_preserve_duplicate_times_and_report_invalid_rows(self):
        self.file.write_text('id,price,qty,quote_qty,time,is_buyer_maker\n' +
                             f'2,101,0.2,20.2,{self.start},true\n' +
                             f'1,100,0.1,10,{self.start},false\n' +
                             f'3,0,0.1,0,{self.start+1},true\n' +
                             f'4,103,0.1,10.3,{self.start+100},true\n')
        result = query_contract([self.file], self.start, self.start+50, 100)
        self.assertFalse(result['sampled'])
        self.assertEqual(result['raw_rows_in_window'], 2)
        self.assertEqual([t[3] for t in result['ticks']], ['1', '2'])
        self.assertEqual(result['header_rows'], 1)
        self.assertEqual(result['invalid_rows_in_source_files'], 1)
        self.assertEqual(result['valid_rows_outside_window'], 1)

    def test_overview_keeps_actual_extrema_and_respects_window(self):
        rows = []
        for i in range(1000):
            price = 1000 if i == 250 else 1 if i == 750 else 100
            rows.append(f'{i},{price},1,{price},{self.start+i},true\n')
        self.file.write_text(''.join(rows))
        result = query_contract([self.file], self.start, self.start+1000, 8)
        self.assertTrue(result['sampled'])
        self.assertEqual(result['raw_rows_in_window'], 1000)
        self.assertLessEqual(len(result['ticks']), 8)
        self.assertIn(1000, [t[1] for t in result['ticks']])
        self.assertIn(1, [t[1] for t in result['ticks']])
        self.assertTrue(all(self.start <= t[0] < self.start+1000 for t in result['ticks']))

    def test_inventory_only_selects_trade_csvs(self):
        self.file.write_text('')
        (self.file.parent / 'unrelated.csv').write_text('')
        selected = inventory(self.file.parent)
        self.assertEqual(list(selected), ['BTCUSDT_260925'])
        self.assertEqual(inventory(self.file.parent, {'ETHUSDT'}), {})


if __name__ == '__main__':
    unittest.main()
