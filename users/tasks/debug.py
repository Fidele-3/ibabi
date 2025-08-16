from celery import shared_task
from users.tasks.fetch_climate_data import fetch_and_store_climate_data as fetch_task

@shared_task
def debug_fetch_climate_data():
    print("🔍 Running debug fetch of climate data...")
    fetch_task.delay()
