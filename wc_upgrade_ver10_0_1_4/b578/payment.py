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

class LoanPayments(models.Model):

    _inherit = 'wc.loan.payment'

#overwrite for b578
    amount2 = fields.Float("Total Amount", digits=(12,2), 
                           compute="compute_amount2",
                           inverse="inverse_amount2")



    @api.depends(
        'is_manual_compute',
        'principal_amount',
        'interest_amount',
        'penalty_amount',
        'amount',
    )
    def compute_amount2(self):
        for p in self:
            if p.is_manual_compute:
                #b578
                p.amount2 = p.principal_amount + p.interest_amount + p.penalty_amount + p.others_amount
            else:
                p.amount2 = p.amount

    def inverse_amount2(self):
        for p in self:
            if p.is_manual_compute:
                p.amount = p.amount2
