import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.main import create_app
from tests.conftest import KURLA

LAT, LON = KURLA


@pytest.fixture
def client(settings, store, monkeypatch):
    # No test may reach the network: geocoding and Overpass are replaced per test.
    def no_network(*a, **kw):
        raise main.requests.ConnectionError("network disabled in tests")

    monkeypatch.setattr(main.requests, "get", no_network)
    monkeypatch.setattr(main.requests, "post", no_network)
    with TestClient(create_app(settings, store)) as c:
        yield c


def sign_up(client, **extra) -> dict:
    r = client.post("/api/users", json={"lat": LAT, "lon": LON, **extra})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_forecast_gives_hours_days_and_ward(client):
    r = client.get("/api/forecast", params={"lat": LAT, "lon": LON, "workload": "heavy", "days": 2})
    body = r.json()
    assert r.status_code == 200
    assert body["location"]["ward"] == "L" and body["location"]["source"] == "sample"
    assert len(body["hours"]) == 48 and len(body["days"]) == 2
    assert body["now"]["level"] in ("safe", "caution", "high", "extreme")
    hour = body["hours"][12]
    assert hour["work_min"] + hour["rest_min"] == 60


def test_lighter_work_and_acclimatisation_are_never_riskier(client):
    def worked(**params):
        hours = client.get("/api/forecast", params={"lat": LAT, "lon": LON, "days": 1, **params}).json()["hours"]
        return [h["work_min"] for h in hours]

    heavy, light = worked(workload="heavy"), worked(workload="light")
    new = worked(workload="heavy", acclimatised=False)
    assert all(l >= h for l, h in zip(light, heavy)) and light != heavy
    assert all(n <= h for n, h in zip(new, heavy)) and new != heavy


def test_bad_input_is_rejected(client):
    assert client.get("/api/forecast", params={"lat": 123, "lon": LON}).status_code == 422
    assert client.get("/api/forecast", params={"lat": LAT, "lon": LON, "workload": "sprint"}).status_code == 422
    r = client.get("/api/plan", params={"lat": LAT, "lon": LON, "duration_hours": 8, "earliest_hour": 10, "latest_hour": 14})
    assert r.status_code == 422


def test_plan_for_tomorrow_returns_ranked_windows(client):
    tomorrow = client.get("/api/forecast", params={"lat": LAT, "lon": LON, "days": 2}).json()["days"][1]["date"]
    r = client.get("/api/plan", params={"lat": LAT, "lon": LON, "duration_hours": 2, "day": tomorrow})
    windows = r.json()["windows"]
    assert r.status_code == 200 and 1 <= len(windows) <= 3
    assert all(w["start"].startswith(tomorrow) for w in windows)
    # 06:00 to 08:00 is the only fully safe two hours before evening in the recorded forecast.
    assert (windows[0]["level"], windows[0]["start"][11:16]) == ("safe", "06:00")


def test_city_has_all_24_wards_with_48_hours(client):
    body = client.get("/api/city").json()
    assert len(body["wards"]) == 24 and len(body["times"]) == 48
    assert sum(w["focus"] for w in body["wards"]) == 6
    assert all(len(w["wbgt_c"]) == 48 for w in body["wards"])
    assert client.get("/api/wards.geojson").json()["features"][0]["properties"]["ward"] == "A"


def test_geocode_finds_mumbai_areas_offline(client):
    body = client.get("/api/geocode", params={"q": "dharavi"}).json()
    assert body["results"][0]["label"] == "Dharavi, Mumbai (G/N ward)"
    assert body["remote_ok"] is False


def test_geocode_adds_places_from_open_meteo(client, monkeypatch):
    class Resp:
        def raise_for_status(self): ...
        def json(self):
            return {"results": [{"name": "Pune", "admin1": "Maharashtra", "country": "India", "latitude": 18.52, "longitude": 73.86}]}

    monkeypatch.setattr(main.requests, "get", lambda *a, **kw: Resp())
    body = client.get("/api/geocode", params={"q": "pune"}).json()
    assert body["results"] == [{"label": "Pune, Maharashtra, India", "lat": 18.52, "lon": 73.86}]


def test_water_points_from_overpass_and_clean_error_when_it_is_down(client, monkeypatch):
    assert client.get("/api/water", params={"lat": LAT, "lon": LON}).status_code == 503

    class Resp:
        def raise_for_status(self): ...
        def json(self):
            return {
                "elements": [
                    {"type": "node", "lat": 19.08, "lon": 72.88, "tags": {"amenity": "drinking_water"}},
                    {"type": "way", "center": {"lat": 19.09, "lon": 72.89}, "tags": {"amenity": "hospital", "name": "City Hospital"}},
                    {"type": "way", "tags": {"amenity": "shelter"}},
                ]
            }

    monkeypatch.setattr(main.requests, "post", lambda *a, **kw: Resp())
    points = client.get("/api/water", params={"lat": LAT, "lon": LON}).json()["points"]
    assert points == [
        {"kind": "water", "name": "", "lat": 19.08, "lon": 72.88},
        {"kind": "hospital", "name": "City Hospital", "lat": 19.09, "lon": 72.89},
    ]


def test_sign_up_stores_only_the_cell_and_labels_the_ward(client):
    r = client.post("/api/users", json={"lat": 19.08763, "lon": 72.88671, "new_to_heat": True})
    user = r.json()["user"]
    assert (user["lat"], user["lon"]) == (19.09, 72.89)
    assert user["area_label"] == "Kurla, Saki Naka (L ward)"
    assert user["new_to_heat"] and user["new_to_heat_until"]
    assert user["tz"] == "Asia/Kolkata"


def test_account_needs_a_valid_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_settings_can_be_changed_and_are_validated(client):
    auth = sign_up(client)
    r = client.patch("/api/me", headers=auth, json={"workload": "light", "paused": True, "peak_reminders": False, "new_to_heat": True})
    user = r.json()
    assert (user["workload"], user["paused"], user["peak_reminders"], user["new_to_heat"]) == ("light", True, False, True)
    assert client.patch("/api/me", headers=auth, json={"new_to_heat": False}).json()["new_to_heat_until"] is None
    assert client.patch("/api/me", headers=auth, json={"work_start": 20}).status_code == 422
    assert client.get("/api/me", headers=auth).json()["work_start"] == 8
    assert client.patch("/api/me", headers=auth, json={"lat": 18.92}).status_code == 422
    assert client.patch("/api/me", headers=auth, json={"whatsapp_number": "12"}).status_code == 422
    moved = client.patch("/api/me", headers=auth, json={"lat": 18.9231, "lon": 72.825}).json()
    assert moved["area_label"].endswith("(A ward)") or moved["area_label"] == "Kurla, Saki Naka (L ward)"


def test_preview_alert_lands_in_inbox_and_stats(client):
    auth = sign_up(client)
    assert client.post("/api/me/alerts/preview", headers=auth).json()["deliveries"] == {"web": "sent"}
    assert client.post("/api/me/alerts/preview", headers=auth).status_code == 201
    alerts = client.get("/api/me/alerts", headers=auth).json()["alerts"]
    assert len(alerts) == 2 and alerts[0]["title"].startswith("Today's heat risk")
    stats = client.get("/api/stats").json()
    assert stats["users"] == 1 and stats["alerts"] == {"test": 2} and stats["delivery_rate"] == 1.0
    today = client.get("/api/me/today", headers=auth).json()
    assert today["day"]["level"] and today["now"]


def test_deleting_the_account_removes_its_alerts_but_keeps_anonymous_totals(client):
    auth = sign_up(client)
    other = sign_up(client)
    client.post("/api/me/alerts/preview", headers=auth)
    assert client.delete("/api/me", headers=auth).status_code == 204
    assert client.get("/api/me", headers=auth).status_code == 401
    assert client.get("/api/me/alerts", headers=other).json()["alerts"] == []
    stats = client.get("/api/stats").json()
    assert stats["users"] == 1 and stats["alerts"] == {"test": 1}


def test_health_and_safety_content(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["scheduler"] is False
    safety = client.get("/api/safety").json()
    assert [n["number"] for n in safety["emergency_numbers"]] == ["108", "112"]
    assert safety["flow"][0]["result"]["call"] is True
