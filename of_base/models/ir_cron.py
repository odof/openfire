# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import threading
import psycopg2
import odoo
from datetime import datetime
from odoo import fields
from odoo.addons.base.ir.ir_cron import ir_cron
from odoo.addons.base.ir.ir_cron import BadModuleState
from odoo.addons.base.ir.ir_cron import BadVersion
from odoo.addons.base.ir.ir_cron import BASE_VERSION
from odoo.addons.base.ir.ir_cron import MAX_FAIL_TIME

_logger = logging.getLogger(__name__)


@classmethod
def _process_jobs(cls, db_name):
    """ Overriding the standard method to add a message when the job execution ends
    See addons/base/ir/ir_cron.py for the original function
    """
    db = odoo.sql_db.db_connect(db_name)
    threading.current_thread().dbname = db_name
    try:
        with db.cursor() as cr:
            # Make sure the database has the same version as the code of
            # base and that no module must be installed/upgraded/removed
            cr.execute("SELECT latest_version FROM ir_module_module WHERE name=%s", ['base'])
            (version,) = cr.fetchone()
            cr.execute("SELECT COUNT(*) FROM ir_module_module WHERE state LIKE %s", ['to %'])
            (changes,) = cr.fetchone()
            if version is None:
                raise BadModuleState()
            elif version != BASE_VERSION:
                raise BadVersion()
            # Careful to compare timestamps with 'UTC' - everything is UTC as of v6.1.
            cr.execute("""SELECT * FROM ir_cron
                            WHERE numbercall != 0
                                AND active AND nextcall <= (now() at time zone 'UTC')
                            ORDER BY priority""")
            jobs = cr.dictfetchall()

        if changes:
            if not jobs:
                raise BadModuleState()
            # nextcall is never updated if the cron is not executed,
            # it is used as a sentinel value to check whether cron jobs
            # have been locked for a long time (stuck)
            parse = fields.Datetime.from_string
            oldest = min([parse(job['nextcall']) for job in jobs])
            if datetime.now() - oldest > MAX_FAIL_TIME:
                odoo.modules.reset_modules_state(db_name)
            else:
                raise BadModuleState()

        for job in jobs:
            lock_cr = db.cursor()
            try:
                # Try to grab an exclusive lock on the job row from within the task transaction
                # Restrict to the same conditions as for the search since the job may have already
                # been run by an other thread when cron is running in multi thread
                lock_cr.execute("""SELECT *
                                    FROM ir_cron
                                    WHERE numbercall != 0
                                        AND active
                                        AND nextcall <= (now() at time zone 'UTC')
                                        AND id=%s
                                    FOR UPDATE NOWAIT""",
                                (job['id'],), log_exceptions=False)

                locked_job = lock_cr.fetchone()
                if not locked_job:
                    _logger.debug("Job `%s` already executed by another process/thread. skipping it", job['name'])
                    continue
                # Got the lock on the job row, run its code
                _logger.info('Starting job `%s`.', job['name'])
                job_cr = db.cursor()
                try:
                    registry = odoo.registry(db_name)
                    registry[cls._name]._process_job(job_cr, job, lock_cr)
                except Exception:
                    _logger.exception('Unexpected exception while processing cron job %r', job)
                finally:
                    job_cr.close()
                    # MODIFICATION OPENFIRE
                    _logger.info('Ending job `%s`.', job['name'])
                    # FIN MODIFICATION OPENFIRE

            except psycopg2.OperationalError, e:
                if e.pgcode == '55P03':
                    # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                    _logger.debug(
                        'Another process/thread is already busy executing job `%s`, skipping it.', job['name'])
                    continue
                else:
                    # Unexpected OperationalError
                    raise
            finally:
                # we're exiting due to an exception while acquiring the lock
                lock_cr.close()

    finally:
        if hasattr(threading.current_thread(), 'dbname'):
            del threading.current_thread().dbname


ir_cron._process_jobs = _process_jobs
