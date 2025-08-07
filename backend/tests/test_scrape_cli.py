from pytest import skip
@skip(allow_module_level=True,reason="Skipping test for AWS scraper functionality")
def test_command_line_interface():
    assert True  # Replace with actual CLI tests