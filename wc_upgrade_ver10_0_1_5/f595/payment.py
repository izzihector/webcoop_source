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
    
    ex_interest_at_date = fields.Float(compute="compute_remain_at_date")
    remain_principal_at_date = fields.Float(compute="compute_remain_at_date")
    remain_otherdue_at_date = fields.Float(compute="compute_remain_at_date")
    remain_penalty_at_date = fields.Float(compute="compute_remain_at_date")
    remain_total_at_date = fields.Float(compute="compute_remain_at_date")


    @api.depends('loan_id.details.total_due')
    def compute_remain_at_date(self):
        self.ensure_one()   

        principal_bal,\
        interest_bal,\
        penalty_bal,\
        others_bal,\
        total_bal = self.get_current_balance()

        self.remain_principal_at_date = principal_bal
        self.ex_interest_at_date = interest_bal
        self.remain_penalty_at_date = penalty_bal
        self.remain_otherdue_at_date = others_bal
        self.remain_total_at_date = total_bal
            
