import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")
auto_scan_job = None

def start_auto_scan(app, interval_minutes=30):
    global auto_scan_job
    from app.utils import set_setting
    if auto_scan_job is None:
        from app.scanner import scan_all_subnets
        auto_scan_job = scheduler.add_job(
            func=scan_all_subnets,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='auto_scan_job',
            name='Auto Scan Subnets',
            replace_existing=True
        )
        if not scheduler.running:
            scheduler.start()
        app.logger.info(f'Auto scan started with interval {interval_minutes} minutes.')
    else:
        # Update interval jika sudah berjalan
        auto_scan_job.reschedule(trigger=IntervalTrigger(minutes=interval_minutes))
        app.logger.info(f'Auto scan interval updated to {interval_minutes} minutes.')
    
    # Simpan status ke database
    set_setting('auto_scan_enabled', 'true')
    set_setting('auto_scan_interval', str(interval_minutes))

def stop_auto_scan(app):
    global auto_scan_job
    from app.utils import set_setting
    if auto_scan_job:
        auto_scan_job.remove()
        auto_scan_job = None
        app.logger.info('Auto scan stopped.')
    
    # Simpan status ke database
    set_setting('auto_scan_enabled', 'false')