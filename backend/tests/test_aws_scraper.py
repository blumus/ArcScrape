from pytest import skip
@skip(allow_module_level=True,reason="Skipping test for AWS scraper functionality")
def test_aws_scraper_functionality():
    assert True  # Replace with actual test logic for AWS scraper functionality