# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import time

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Loan(models.Model):
    _inherit = "wc.loan"

    @api.model
    def get_aging_data(self, date_as_of=False):
        self.ensure_one()

        if not date_as_of:
            date_as_of = fields.Date.context_today(self)

        total = 0.0
        current = 0.0
        pd_30 = 0.0
        pd_60 = 0.0
        pd_90 = 0.0
        pd_180 = 0.0
        pd_365 = 0.0    #181-365
        pd_over1y = 0.0
        pd_total = 0.0

        d0 = fields.Date.from_string(date_as_of)

        for det in self.details:
            pdue = max(det.principal_due - det.principal_paid, 0.0)
            if pdue>EPS:
                date_due = fields.Date.from_string(det.date_due)
                days = (d0-date_due).days
                total += pdue
                if days<1:
                    current += pdue
                elif days<=30:
                    pd_30 += pdue
                    pd_total += pdue
                elif days<=60:
                    pd_60 += pdue
                    pd_total += pdue
                elif days<=90:
                    pd_90 += pdue
                    pd_total += pdue
                elif days<=180:
                    pd_180 += pdue
                    pd_total += pdue
                elif days<=365:
                    pd_365 += pdue
                    pd_total += pdue
                else:
                    pd_over1y += pdue
                    pd_total += pdue

        return {
            'total': total,
            'current': current,
            'pd_30': pd_30,
            'pd_60': pd_60,
            'pd_90': pd_90,
            'pd_180': pd_180,
            'pd_365': pd_365,
            'pd_over1y': pd_over1y,
            'pd_total': pd_total,
        }

#
