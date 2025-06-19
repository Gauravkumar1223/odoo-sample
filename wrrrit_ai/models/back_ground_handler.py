import threading
import functools
from odoo import fields, api
import logging
import odoo

_logger = logging.getLogger(__name__)


def run_background_action(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        cr = args[0].env.cr
        uid = args[0].env.uid
        context = args[0].env.context
        action_name = func.__name__.replace("_", " ").capitalize()
        _logger.info(f"Running background action: {action_name}")

        # Create a background action record
        background_action_env = args[0].env["background.action"]
        action_record = background_action_env.create(
            {
                "name": action_name,
                "user_id": args[0].env.user.id,
                "status": "in_progress",
                "additional_info": "Action started",
                "start_time": fields.Datetime.now(),
            }
        )

        def action_callback(result, action_record):
            try:
                _logger.info(f"Action completed successfully: {result}")
                with api.Environment.manage():
                    new_cr = odoo.sql_db.db_connect(cr.dbname).cursor()
                    new_env = api.Environment(new_cr, uid, context)
                    action_record.with_env(new_env).write(
                        {
                            "status": "completed",
                            "end_time": fields.Datetime.now(),
                            "result": str(result),
                            "additional_info": "Action completed successfully",
                        }
                    )
                    new_cr.commit()
            except Exception as e:
                _logger.error(f"Action failed: {e}")
                with api.Environment.manage():
                    new_cr = odoo.sql_db.db_connect(cr.dbname).cursor()
                    new_env = api.Environment(new_cr, uid, context)
                    action_record.with_env(new_env).write(
                        {
                            "status": "failed",
                            "end_time": fields.Datetime.now(),
                            "result": str(e),
                            "additional_info": "Action failed",
                        }
                    )
                    new_cr.commit()
            finally:
                if new_cr:
                    new_cr.close()

        def run():
            try:
                result = func(*args, **kwargs)
                action_callback(result, action_record)
            except Exception as e:
                _logger.error(f"Exception in background thread: {e}")

        thread = threading.Thread(target=run, args=())
        thread.start()

        return action_record.id

    return wrapper
