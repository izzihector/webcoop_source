# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanType(models.Model):
    _inherit = "wc.loan.type"
    
    @api.onchange('is_interest_epr')
    def onchange_is_interest_epr(self):
        pass


    @api.onchange('is_interest_epr','is_interest_deduction_first')
    def onchange_is_interest_deduction_first(self):
        self.ensure_one()
        if self.is_interest_deduction_first:
            self.is_fixed_payment_amount = False

    @api.constrains('is_interest_deduction_first','is_fixed_payment_amount')
    def validate_is_interest_deduction_first(self):
        if self.is_interest_deduction_first and self.is_fixed_payment_amount:
            raise ValidationError(_("You cannot select Fixed Amount in case Interest Advance Deduction."))


