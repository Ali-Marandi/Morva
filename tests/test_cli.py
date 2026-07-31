import contextlib
import io
import unittest

from morva.cli import main, point_load, udl


class CliTests(unittest.TestCase):
    def test_parsers(self):
        self.assertEqual(point_load("12@2.5").magnitude, 12.0)
        self.assertEqual(udl("3@1:4").end, 4.0)

    def test_cli_output(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                [
                    "--length",
                    "10",
                    "--point-load",
                    "20@5",
                    "--stations",
                    "3",
                ]
            )
        self.assertEqual(status, 0)
        self.assertIn("left_reaction_kN: 10.000", output.getvalue())
        self.assertIn("5.000,-10.000,50.000", output.getvalue())


if __name__ == "__main__":
    unittest.main()
