from pytest import skip
@skip(allow_module_level=True,reason="Skipping test for AWS scraper functionality")
def test_hello_world():
    assert "Hello, World!" == "Hello, World!"