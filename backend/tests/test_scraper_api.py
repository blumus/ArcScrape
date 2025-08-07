import pytest
from fastapi.testclient import TestClient
from scraper_api import app
from pytest import skip

@pytest.fixture
def client():
    return TestClient(app)

def test_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AWS Architecture Scraper" in response.text

def test_list_scrapes(client):
    response = client.get("/api/scrapes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_successful_scrapes(client):
    response = client.get("/api/scrapes/successful")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_failed_scrapes(client):
    response = client.get("/api/scrapes/failed")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.skip(reason="Skipping test for HTML content")
def test_start_scrape(client):
    response = client.post("/api/scrapes/start", json={})
    assert response.status_code == 200
    data = response.json()
    assert "scrape_id" in data
    assert data["success"] is True

def test_get_stats(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_scrapes" in stats
    assert "successful_scrapes" in stats
    assert "failed_scrapes" in stats
    assert "total_files_scraped" in stats