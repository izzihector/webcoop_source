# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Loan(models.Model):
    _inherit = "wc.loan"

    @api.model
    def get_skip_dates(self, date_start):
        res =  super(Loan, self).get_skip_dates(date_start)
        holidays = self.env['ez.holiday'].search([
            ('date','>=',date_start)
        ])
        for h in holidays:
            res.append(h.date)
        return res
