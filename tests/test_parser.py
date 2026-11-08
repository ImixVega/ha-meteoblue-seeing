"""Offline regression tests for the HTML parser (no private saved pages needed)."""
from importlib import util
from pathlib import Path
import sys
import unittest

PARSER = (Path(__file__).resolve().parents[1] / "custom_components" / "meteoblue_seeing" / "parser.py")
spec = util.spec_from_file_location("standalone_seeing_parser", PARSER)
parser = util.module_from_spec(spec)
sys.modules[spec.name] = parser
spec.loader.exec_module(parser)


def fixture() -> str:
    """Tiny synthetic server-rendered table with the same column ordering."""
    days = ["2026-11-08", "2026-11-09", "2026-11-10"]
    content = ['<table class="table-seeing"><tbody>']
    for day_index, day in enumerate(days):
        content.append(f'<tr><td class="new-day">Sun {day} <pre>sunrise: 06:46 sunset: 16:06 moonphase: 1%</pre></td></tr>')
        for hour in range(1, 15):
            fields = [str(hour), "10", "20", "30", "1.30", "4", "2", "8 m/s", "05.7", "06.4", "0.6 K", "-2 C", "83%"]
            tds = ''.join(f'<td>{value}</td>' for value in fields)
            content.append(f'<tr class="hour-row night" data-day="{day_index}" data-hour="{hour}">{tds}<td><table><tr><td>Venus</td></tr></table></td></tr>')
    content.append('</tbody></table>')
    return ''.join(content)


class SeeingParserTests(unittest.TestCase):
    def test_reads_three_days_hourly_records(self):
        forecast = parser.parse_seeing_html(fixture(), "Europe/Warsaw")
        self.assertEqual(len(forecast.hours), 42)
        self.assertEqual(len(forecast.days), 3)
        self.assertEqual(forecast.hours[0].time.isoformat(), "2026-11-08T01:00:00+01:00")
        self.assertEqual(forecast.hours[0].seeing_arcsec, 1.3)
        self.assertEqual(forecast.hours[0].seeing_1, 4)
        self.assertEqual(forecast.hours[0].jetstream, 8.0)
        self.assertEqual(forecast.hours[0].humidity, 83)
        self.assertEqual(forecast.hours[0].cloud_low, 10)

    def test_missing_table_is_error(self):
        with self.assertRaises(parser.SeeingParseError):
            parser.parse_seeing_html("<html><body>Request blocked</body></html>", "Europe/Warsaw")

    def test_invalid_timezone_is_error(self):
        with self.assertRaises(parser.SeeingParseError):
            parser.parse_seeing_html(fixture(), "Not/A_Timezone")


if __name__ == "__main__":
    unittest.main()
