# utils.py
import requests
from datetime import date, timedelta
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_live_data(latitude=None, longitude=None, cell=None, past_days=90):
    """
    Fetch live climate data using Open-Meteo API.
    Can fetch either:
        - Next 24h forecast (if past_days=None)
        - Past 'past_days' of data (if past_days provided)
    """
    if latitude is None or longitude is None:
        if cell is None:
            raise ValueError("Either latitude/longitude or cell instance must be provided")
        latitude = cell.latitude
        longitude = cell.longitude

    if not latitude or not longitude:
        raise ValueError("Missing latitude/longitude information")

    result = {
        "next_24h_forecast": None,
        "past_3_months_data": None
    }

    try:
        # Fetch next 24h forecast
        forecast_params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation",
            "forecast_days": 1,
            "timezone": "auto"
        }
        resp_forecast = requests.get(OPEN_METEO_FORECAST_URL, params=forecast_params, timeout=15)
        resp_forecast.raise_for_status()
        result["next_24h_forecast"] = resp_forecast.json()

        # Fetch past climate data if requested
        if past_days:
            end_date = date.today()
            start_date = end_date - timedelta(days=past_days)
            archive_params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto"
            }
            resp_historical = requests.get(OPEN_METEO_ARCHIVE_URL, params=archive_params, timeout=20)
            resp_historical.raise_for_status()
            result["past_3_months_data"] = resp_historical.json()

    except requests.RequestException as e:
        logger.error(f"🌐 Network/API error fetching live data for lat={latitude}, lon={longitude}: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching live data for lat={latitude}, lon={longitude}: {e}")

    return result
