from django.test import SimpleTestCase
from CoreFisica.utils import parse_input


class ParseInputTests(SimpleTestCase):
    def test_parse_normal_and_empty(self):
        res = parse_input("1 14H L-V / 9H S / 5H D")
        self.assertEqual(len(res), 7)
        self.assertEqual(res[0]["dia"], 1)
        self.assertEqual(res[-1]["dia"], 7)
        self.assertEqual(parse_input("") , [])

    def test_parse_comma_and_name_accent(self):
        res = parse_input("14H L,M,X")
        self.assertEqual([r['dia'] for r in res], [1, 2, 3])
        res2 = parse_input("8H Miércoles")
        self.assertTrue(any(r['dia'] == 3 for r in res2))

    def test_parse_circular_range_and_errors(self):
        res = parse_input("10H V-L")
        # V-L -> V(5), S(6), D(7), L(1)
        self.assertEqual([r['dia'] for r in res][:4], [5, 6, 7, 1])
        with self.assertRaises(ValueError):
            parse_input("bad format")
