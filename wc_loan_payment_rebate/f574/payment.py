# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging


_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanPayments(models.Model):
    _inherit = "wc.loan.payment"
    
    def check_if_reversable(self):
        if len(self.loan_id.payment_rebate_ids)==0:
            return True
        remain=self.loan_id.rebatable_amount
        if self.loan_id.rebatable_payment_type == 'interest_only':
            list =['INT']
        elif self.loan_id.rebatable_payment_type == 'int_penalty':
            list =['INT','PEN']
        else:
            list =['INT']
        
        for dist in self.distributions:
            if dist.code in list:
                remain -= dist.amount

        if remain < EPS:
            raise ValidationError(_("Cannot revsere this amount(already part of this payment has been rebated)."))
        return True

    @api.multi
    def reverse_payment(self):
        if self.check_if_reversable():
            super(LoanPayments,self).reverse_payment()
#
