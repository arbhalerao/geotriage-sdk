import pytest

from geotriage import Model, Prefilter, Requires, Score, Thresholds, check_model, split_output


def test_a_conformant_model_has_no_problems(model):
    assert check_model(model) == []


def test_primary_score_is_derived_from_the_declarations(model):
    assert model.primary_score == "mean_c"
    assert sorted(model.default_thresholds) == ["hot_fraction", "mean_c"]


def test_model_without_a_primary_score_is_rejected():
    class NoPrimary(Model):
        slug, name = "no-primary", "No Primary"
        requires = Requires(bands=["green"])
        scores = {"a": Score(thresholds=Thresholds((0, 1), (1, 2)))}

        def run(self, bands):
            return {"a": 1.0}

    assert any("primary" in p for p in check_model(NoPrimary()))


def test_model_with_two_primary_scores_is_rejected():
    class TwoPrimary(Model):
        slug, name = "two-primary", "Two Primary"
        requires = Requires(bands=["green"])
        t = Thresholds((0, 1), (1, 2))
        scores = {"a": Score(primary=True, thresholds=t), "b": Score(primary=True, thresholds=t)}

        def run(self, bands):
            return {"a": 1.0, "b": 2.0}

    assert any("primary" in p for p in check_model(TwoPrimary()))


def test_score_without_thresholds_is_rejected():
    class NoThresholds(Model):
        slug, name = "no-thresholds", "No Thresholds"
        requires = Requires(bands=["green"])
        scores = {"a": Score(primary=True)}

        def run(self, bands):
            return {"a": 1.0}

    assert any("thresholds" in p for p in check_model(NoThresholds()))


def test_duplicate_required_bands_are_rejected():
    class Duplicate(Model):
        slug, name = "duplicate", "Duplicate Bands"
        requires = Requires(bands=["green", "green"])
        scores = {"a": Score(primary=True, thresholds=Thresholds((0, 1), (1, 2)))}

        def run(self, bands):
            return {"a": 1.0}

    assert any("duplicate" in p.lower() for p in check_model(Duplicate()))


def test_declaring_a_prefilter_without_implementing_screen_is_rejected():
    class Ungated(Model):
        slug, name = "ungated", "Prefilter Without A Gate"
        requires = Requires(bands=["green"])
        prefilter = Prefilter(bands=["green"], gsd_m=300.0)
        scores = {"a": Score(primary=True, thresholds=Thresholds((0, 1), (1, 2)))}

        def run(self, bands):
            return {"a": 1.0}

    problems = check_model(Ungated())
    assert any("screen()" in p for p in problems), problems


def test_an_implemented_gate_is_conformant(screened_model):
    assert check_model(screened_model) == []


def test_misspelled_score_name_raises_instead_of_vanishing(model):
    with pytest.raises(ValueError) as exc:
        split_output(model, {"mean_celsius": 20.0, "hot_fraction": 0.1})
    assert "mean_c" in str(exc.value)


def test_undeclared_keys_are_kept_as_metadata(model):
    scores, metadata = split_output(model, {"mean_c": 20.0, "hot_fraction": 0.1, "valid_pixel_count": 99})
    assert scores == {"mean_c": 20.0, "hot_fraction": 0.1}
    assert metadata == {"valid_pixel_count": 99}


def test_none_is_an_acceptable_score_for_a_thin_scene(model):
    scores, _ = split_output(model, {"mean_c": None, "hot_fraction": None})
    assert scores["mean_c"] is None


def test_non_dict_output_is_rejected(model):
    with pytest.raises(ValueError):
        split_output(model, [1, 2, 3])
