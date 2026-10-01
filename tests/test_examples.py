from pathlib import Path

import pytest

from adoptsignal.examples import DEMOS, demo_csv_bytes


ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("filename", sorted(DEMOS))
def test_in_app_demo_is_identical_to_the_committed_example(filename):
    # The app generates its demos in memory, so they also work from an installed wheel; they must stay
    # byte-identical to the committed files that the docs and tests refer to.
    committed = (ROOT / "examples" / filename).read_bytes().replace(b"\r\n", b"\n")
    assert demo_csv_bytes(filename) == committed
