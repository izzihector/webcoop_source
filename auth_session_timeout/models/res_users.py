# -*- coding: utf-8 -*-
# (c) 2015 ACSONE SA/NV, Dhinesh D

# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from os.path import getmtime
from time import time
from os import utime
import threading

from odoo import api, http, models

_logger = logging.getLogger(__name__)
DEBUG = 1

_sessions = {}
_lock = threading.RLock()
def session_set(sid, tm):
    global _lock
    res = False
    if _lock.acquire(False):
        _sessions[sid] = tm
        _lock.release()
        res = True
    elif DEBUG:
        _logger.debug("session_set: locked")
    return res

def session_del(sid):
    global _lock
    res = False
    if _lock.acquire(False):
        del _sessions[sid]
        _lock.release()
        res = True
    elif DEBUG:
        _logger.debug("session_del: locked")
    return res

def session_get(sid):
    global _lock
    res = False
    if _lock.acquire(False):
        res = _sessions.get(sid)
        _lock.release()
    elif DEBUG:
        _logger.debug("session_get: locked")
    return res


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_cr_context
    def _auth_timeout_get_ignored_urls(self):
        """Pluggable method for calculating ignored urls
        Defaults to stored config param
        """
        params = self.env['ir.config_parameter']
        return params._auth_timeout_get_parameter_ignored_urls()

    @api.model_cr_context
    def _auth_timeout_deadline_calculate(self):
        """Pluggable method for calculating timeout deadline
        Defaults to current time minus delay using delay stored as config
        param.
        """
        params = self.env['ir.config_parameter']
        delay = params._auth_timeout_get_parameter_delay()
        if delay <= 0:
            return False
        return time() - delay

    @api.model_cr_context
    def _auth_timeout_session_terminate(self, session):
        """Pluggable method for terminating a timed-out session

        This is a late stage where a session timeout can be aborted.
        Useful if you want to do some heavy checking, as it won't be
        called unless the session inactivity deadline has been reached.

        Return:
            True: session terminated
            False: session timeout cancelled
        """
        if session.db and session.uid:
            session.logout(keep_db=True)
        return True

    @api.model_cr_context
    def _auth_timeout_check(self):
        """Perform session timeout validation and expire if needed."""

        if not http.request:
            return

        session = http.request.session

        # Calculate deadline
        deadline = self._auth_timeout_deadline_calculate()
        #_logger.debug("**check session timeout: deadline=%s", deadline)

        # Check if past deadline
        expired = False
        if deadline is not False:

            session_time = session_get(session.sid)
            if not session_time:
                session_time = time()
                #session_set(session.sid, session_time)
                _logger.debug("**check session: id=%s new=%s",
                    session.sid[:4],
                    session_time
                )
            expired = session_time < deadline
            if DEBUG:
                _logger.debug("**check session: id=%s session=%s deadline=%s diff=%s expired=%s",
                    session.sid[:4],
                    session_time,
                    deadline,
                    deadline - session_time,
                    expired,
                )

        # Try to terminate the session
        terminated = False
        if expired:
            terminated = self._auth_timeout_session_terminate(session)
            lock_ok = session_del(session.sid)
            _logger.debug("**check session: id=%s expired terminated=%s lock_ok=%s",
                session.sid[:4],
                terminated,
                lock_ok
            )

        # If session terminated, all done
        if terminated:
            return

        # Else, conditionally update session modified and access times
        ignored_urls = self._auth_timeout_get_ignored_urls()

        if http.request.httprequest.path not in ignored_urls:
            session_time = time()
            lock_ok = session_set(session.sid, session_time)
            if DEBUG:
                _logger.debug("**check session: id=%s settime=%s lock_ok=%s",
                    session.sid[:4],
                    session_time,
                    lock_ok
                )
