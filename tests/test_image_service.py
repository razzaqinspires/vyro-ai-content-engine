import pytest
from vyro_ai_content_engine.images import ImageGenerationService


def test_demo_namespace_is_not_plain_user_id():
    namespace = ImageGenerationService._demo_namespace("VYRO-DEMO-1234ABCD")
    assert len(namespace) == 24
    assert namespace != "VYRO-DEMO-1234ABCD"


def test_rejects_invalid_demo_id():
    with pytest.raises(ValueError):
        ImageGenerationService._demo_namespace("guest-123")
