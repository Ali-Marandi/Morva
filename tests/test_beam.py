import unittest

from morva import Beam, PointLoad, UDL


class BeamTests(unittest.TestCase):
    def test_central_point_load(self):
        beam = Beam(10.0, point_loads=(PointLoad(20.0, 5.0),))
        self.assertEqual(beam.reactions(), (10.0, 10.0))
        self.assertAlmostEqual(beam.moment_at(5.0), 50.0)
        self.assertAlmostEqual(beam.moment_at(10.0), 0.0)

    def test_full_span_udl(self):
        beam = Beam(6.0, udls=(UDL(4.0, 0.0, 6.0),))
        self.assertEqual(beam.reactions(), (12.0, 12.0))
        self.assertAlmostEqual(beam.shear_at(3.0), 0.0)
        self.assertAlmostEqual(beam.moment_at(3.0), 18.0)
        self.assertAlmostEqual(beam.moment_at(6.0), 0.0)

    def test_asymmetric_combination_satisfies_equilibrium(self):
        beam = Beam(
            8.0,
            point_loads=(PointLoad(20.0, 3.0),),
            udls=(UDL(5.0, 2.0, 6.0),),
        )
        left, right = beam.reactions()
        self.assertAlmostEqual(left + right, 40.0)
        self.assertAlmostEqual(right * 8.0, 20.0 * 3.0 + 20.0 * 4.0)
        self.assertAlmostEqual(beam.moment_at(8.0), 0.0)

    def test_rejects_load_outside_span(self):
        with self.assertRaisesRegex(ValueError, "within"):
            Beam(5.0, point_loads=(PointLoad(1.0, 5.1),))

    def test_sampling_includes_both_supports(self):
        results = Beam(4.0).sample(5)
        self.assertEqual([result.position for result in results], [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
