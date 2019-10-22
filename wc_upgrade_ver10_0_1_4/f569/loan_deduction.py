# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Deductions(models.Model):
    _inherit = "wc.loan.deduction"

    amount_rate_per_principal = fields.Float("Amount/Principal(%)", 
                                             compute='compute_ded_amount_per_prin',
                                             digits=(12,4))

    @api.depends('amount','loan_id.amount')
    def compute_ded_amount_per_prin(self):
        for d in self:
            if d.loan_id.amount >0:
                d.amount_rate_per_principal = round(d.amount/d.loan_id.amount*100,4)


