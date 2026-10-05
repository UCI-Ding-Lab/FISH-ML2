from fishGUI_multichannel.services.pairing import match_quality_is_good


def test_center_inside_is_always_kept():
    assert match_quality_is_good(True, containment=0.0, distance=1.0)


def test_containment_must_reach_sixty_percent():
    assert match_quality_is_good(False, containment=0.6, distance=1.0)
    assert match_quality_is_good(False, containment=0.61, distance=1.0)
    assert not match_quality_is_good(False, containment=0.59, distance=1.0)


def test_distance_must_be_within_five_percent_of_diagonal():
    assert match_quality_is_good(False, containment=0.0, distance=0.05)
    assert match_quality_is_good(False, containment=0.0, distance=0.04)
    assert not match_quality_is_good(False, containment=0.0, distance=0.06)
