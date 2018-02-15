import pytest

from lots_admin.look_ups import APPLICATION_STATUS
from lots_admin.utils import step_from_status, InvalidStepError


def test_step_from_valid_status():
    for idx, short_name in enumerate(APPLICATION_STATUS.keys(), start=2):
        assert step_from_status(short_name) == idx

def test_step_from_invalid_status():
    with pytest.raises(InvalidStepError) as exception:
        step_from_status('warbgarble')

    assert '"warbgarble" is not in available step keys' in str(exception)