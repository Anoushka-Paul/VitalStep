"""Regression tests for the production Palm Press inference path."""
from app.ml_service import MLModelService, ModelPredictionError
from app.schemas import MLPredictionRequest


def request() -> MLPredictionRequest:
    return MLPredictionRequest(
        trial1=30.0,
        trial2=31.0,
        trial3=29.0,
        hand="right",
        posture="Sitting",
        age=65,
        gender="Female",
        height=160.0,
        weight=62.0,
        palm_length=17.0,
        palm_width=8.0,
        knuckle_length=14.0,
        dominant_hand="right",
    )


def test_enhanced_model_response_is_explicit_and_complete():
    service = MLModelService()
    assert service.load_model(), service.load_error

    result = service.predict(request(), save=False)

    assert result.model_source == "latest_model"
    assert result.fallback_reason is None
    assert result.expected_lower_kg <= result.expected_median_kg <= result.expected_upper_kg
    assert len(result.recommendations) == 5
    assert result.recommendations[1].startswith("Nutrition:")
    assert result.recommendations[2].startswith("Movement:")
    assert result.recommendations[3].startswith("Daily habits:")
    assert result.recommendations[4].startswith("Follow-up:")


def test_fallback_is_used_only_when_the_model_cannot_load():
    service = MLModelService()
    service.model_path = service.model_path / "missing-for-test"
    assert not service.load_model()

    result = service.predict(request(), save=False)

    assert result.model_source == "fallback_model"
    assert result.model_version == "fallback-rules"
    assert result.fallback_reason
    assert result.expected_lower_kg is None


def test_loaded_model_failure_does_not_switch_to_fallback():
    service = MLModelService()
    assert service.load_model(), service.load_error
    service.model["models"]["lower"] = object()

    try:
        service.predict(request(), save=False)
    except ModelPredictionError:
        pass
    else:
        raise AssertionError("A loaded-model failure must not return a fallback prediction")
