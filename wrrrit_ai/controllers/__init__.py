# -*- coding: utf-8 -*-

from . import controllers
from . import long_task_controller, section_controller
from . import wrrrit_realtime_service
import atexit
import signal

# Instantiate the service to run it on startup
# _realtime_service_instance =
realtime_service = wrrrit_realtime_service.RealTimeService()
#
#
# atexit.register(realtime_service.stop_service)
#
#
# def signal_handler(sig, frame):
#     realtime_service.stop_service()
#
# signal.signal(signal.SIGTERM, signal_handler)
