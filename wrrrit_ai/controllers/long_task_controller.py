import time

from odoo import http
from odoo.http import request
import logging


class LongTaskController(http.Controller):
    @http.route("/long_task/trigger", type="json", auth="user")
    def trigger_long_task(self, task_id):
        logging.info("Triggering long task for task ID: %s", task_id)
        time.sleep(2)
        return {"status": "Started..."}

    @http.route("/long_task/status", type="json", auth="user")
    def get_task_status(self, task_id):
        time.sleep(5)
        logging.info("Getting task status for task ID: %s", task_id)
        return {"status": "Running..."}
