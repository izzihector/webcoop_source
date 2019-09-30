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
    is_interest_deduction_first = fields.Boolean("Interest Deduct at Disbursement",help="Select this flag if you deduct total interest at disbursement.(you can select this in case straight loan only)")
    
    @api.constrains('is_interest_deduction_first')
    def validate_is_interest_deduction_first(self):
        for rec in self:
            if rec.is_interest_deduction_first:
                if not rec.is_interest_epr:
                    raise ValidationError(_("You can select [Interest Deduct at Disbursement] only in case straight loan."))
            return True
        
    @api.onchange('is_interest_epr')
    def onchange_is_interest_epr(self):
        if not self.is_interest_epr:
            self.is_interest_deduction_first = False
            

 
