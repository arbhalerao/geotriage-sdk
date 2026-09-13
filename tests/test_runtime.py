import pytest

from geotriage.runtime import MODEL_ENV, PROVIDER_ENV, declared_target, load_declared


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(MODEL_ENV, raising=False)
    monkeypatch.delenv(PROVIDER_ENV, raising=False)


def test_a_model_image_declares_itself(monkeypatch):
    monkeypatch.setenv(MODEL_ENV, "mypkg.detectors:ShipDetector")
    assert declared_target() == (MODEL_ENV, "mypkg.detectors:ShipDetector")


def test_a_provider_image_declares_itself(monkeypatch):
    monkeypatch.setenv(PROVIDER_ENV, "mypkg.archives:AcmeArchive")
    assert declared_target() == (PROVIDER_ENV, "mypkg.archives:AcmeArchive")


def test_declaring_neither_is_refused():
    with pytest.raises(SystemExit) as exc:
        declared_target()
    assert MODEL_ENV in str(exc.value) and PROVIDER_ENV in str(exc.value)


def test_declaring_both_is_refused(monkeypatch):
    monkeypatch.setenv(MODEL_ENV, "a:B")
    monkeypatch.setenv(PROVIDER_ENV, "c:D")
    with pytest.raises(SystemExit) as exc:
        declared_target()
    assert "never both" in str(exc.value)


def test_an_empty_declaration_counts_as_unset(monkeypatch):
    """the base image sets both to "" so that an author's ENV line overrides one of them"""
    monkeypatch.setenv(MODEL_ENV, "")
    monkeypatch.setenv(PROVIDER_ENV, "mypkg.archives:AcmeArchive")
    assert declared_target() == (PROVIDER_ENV, "mypkg.archives:AcmeArchive")


def test_a_malformed_target_names_the_shape_expected(monkeypatch):
    monkeypatch.setenv(MODEL_ENV, "mypkg.detectors.ShipDetector")
    with pytest.raises(SystemExit) as exc:
        load_declared()
    assert "package.module:ClassName" in str(exc.value)


def test_a_missing_module_is_named(monkeypatch):
    monkeypatch.setenv(MODEL_ENV, "no_such_module_here:Thing")
    with pytest.raises(SystemExit) as exc:
        load_declared()
    assert "no_such_module_here" in str(exc.value)


def test_a_missing_class_lists_what_the_module_defines(monkeypatch):
    monkeypatch.setenv(MODEL_ENV, "json:NotInJson")
    with pytest.raises(SystemExit) as exc:
        load_declared()
    message = str(exc.value)
    assert "NotInJson" in message and "dumps" in message
