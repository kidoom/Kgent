"""Smoke tests for kagent package."""


def test_import():
    """Verify kagent package can be imported."""
    import kagent

    assert kagent is not None


def test_import_submodules():
    """Verify kagent submodules can be imported."""
    import kagent.memory
    import kagent.context

    assert kagent.memory is not None
    assert kagent.context is not None
