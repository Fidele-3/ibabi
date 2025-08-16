import requests
from datetime import date, timedelta
from django.utils import timezone
from celery import shared_task
from users.models.addresses import Cell
from report.models import CellClimateData
import logging

logger = logging.getLogger(__name__)

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@shared_task(bind=True, max_retries=3)
def fetch_24h_forecast(self):
    """
    Fetches next 24 hours forecast for all cells.
    Scheduled: every 1 hour via Celery Beat.
    Stores in `next_24h_forecast` JSON field in CellClimateData.
    """
    cells = Cell.objects.all()
    logger.info(f"Starting 24h forecast fetch for {cells.count()} cells...")

    for i, cell in enumerate(cells, start=1):
        lat, lon = cell.latitude, cell.longitude
        if not lat or not lon:
            logger.warning(f"[{i}/{cells.count()}] Skipping {cell.name} - Missing coordinates")
            continue

        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,precipitation",
                "forecast_days": 1,
                "timezone": "auto"
            }
            resp = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=15)
            resp.raise_for_status()
            forecast_data = resp.json()

            CellClimateData.objects.update_or_create(
                cell=cell,
                defaults={
                    "next_24h_forecast": forecast_data,
                    "forecast_fetched_at": timezone.now()
                }
            )
            logger.info(f"[{i}/{cells.count()}] ✅ 24h forecast updated for cell {cell.name}")

        except requests.RequestException as e:
            logger.error(f"[{i}/{cells.count()}] 🌐 Network/API error for cell {cell.name}: {e}")
            self.retry(countdown=60)
        except Exception as e:
            logger.error(f"[{i}/{cells.count()}] ❌ Unexpected error for cell {cell.name}: {e}")


@shared_task(bind=True, max_retries=2)
def fetch_past_3months_data(self):
    """
    Fetches past 3 months climate data for all cells.
    Scheduled: weekly via Celery Beat.
    Stores in `past_3_months_data` JSON field in CellClimateData.
    """
    today = date.today()
    start_date = today - timedelta(days=90)
    end_date = today
    cells = Cell.objects.all()
    logger.info(f"Starting past 3 months data fetch for {cells.count()} cells...")

    for i, cell in enumerate(cells, start=1):
        lat, lon = cell.latitude, cell.longitude
        if not lat or not lon:
            logger.warning(f"[{i}/{cells.count()}] Skipping {cell.name} - Missing coordinates")
            continue

        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto"
            }
            resp = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=20)
            resp.raise_for_status()
            historical_data = resp.json()

            CellClimateData.objects.update_or_create(
                cell=cell,
                defaults={
                    "past_3_months_data": historical_data,
                    "historical_fetched_at": timezone.now()
                }
            )
            logger.info(f"[{i}/{cells.count()}] ✅ Past 3 months data updated for cell {cell.name}")

        except requests.RequestException as e:
            logger.error(f"[{i}/{cells.count()}] 🌐 Network/API error for cell {cell.name}: {e}")
            self.retry(countdown=120)
        except Exception as e:
            logger.error(f"[{i}/{cells.count()}] ❌ Unexpected error for cell {cell.name}: {e}")
