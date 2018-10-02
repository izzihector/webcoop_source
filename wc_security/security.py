# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

import re
from odoo import http
from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

"""
executables = set([
    'ACTION',
    'APK',
    'APP',
    'BAT',
    'BIN',
    'CMD',
    'COM',
    'COMMAND',
    'CPL',
    'CSH',
    'EXE',
    'GADGET',
    'INF1',
    'INS',
    'INX',
    'IPA',
    'ISU',
    'JOB',
    'JSE',
    'KSH',
    'LNK',
    'MSC',
    'MSI',
    'MSP',
    'MST',
    'OSX',
    'OUT',
    'PAF',
    'PIF',
    'PRG',
    'PS1',
    'REG',
    'RGS',
    'RUN',
    'SCR',
    'SCT',
    'SHB',
    'SHS',
    'U3P',
    'VB',
    'VBE',
    'VBS',
    'VBSCRIPT',
    'WORKFLOW',
    'WS',
    'WSF',
    'WSH',
    #reject packed files
    '7Z',
    'DMG',
    'GZ',
    'ISO',
    'JAR',
    'RAR',
    'TAR',
    'ZIP',
    'TGZ',
    'TAR',
])

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    #disable upload of executables
    @api.model
    def check(self, mode, values=None):
        res = super(IrAttachment, self).check(mode, values=values)
        if mode == 'write' and 'datas_fname' in values:
            fname = values.get('datas_fname',"X.X")
            ext = fname.split('.')[-1].upper()
            _logger.debug("check attach: fn=%s ext=%s", fname, ext)
            if ext in executables:
                raise Warning(_("Sorry, you are not allowed to attach executable files.\n%s") % fname)
        return res

"""

db_filter_org = http.db_filter

def db_filter(dbs, httprequest=None):
    dbs = db_filter_org(dbs, httprequest)
    httprequest = httprequest or http.request.httprequest
    h = httprequest.environ.get('HTTP_X_EZTECH_HOST')
    if h:
        d, _, r = h.partition('.')
        #_logger.debug("**db_filter2: d=%s h=%s", d, h)
        dbs = [db for db in dbs if re.match("^%s.*$" % d, db)]
    return dbs

http.db_filter = db_filter
