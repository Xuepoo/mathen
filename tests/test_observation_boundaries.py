import unittest

from scripts.validate_observation_boundaries import validate_all


class ObservationBoundaryTests(unittest.TestCase):
    def test_accepted_observation_boundaries_validate(self) -> None:
        validate_all()


if __name__ == "__main__":
    unittest.main()
