# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
from ConfigParser import MAX_INTERPOLATION_DEPTH

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanType(models.Model):
    _inherit = "wc.loan.type"

    default_amount = fields.Float(string="Default Amount",help="set default loan amount in necessary")
    
    @api.constrains('is_check_by_principal_range','min_principal','max_principal','default_amount')
    def check_principal_range_value(self):
        super(LoanType, self).check_principal_range_value()    
        if self.is_check_by_principal_range and self.default_amount>0:
            if self.default_amount > self.max_principal:
                raise ValidationError(_("principal value range is inconsistent: Default=%s Min=%s Max=%s") % (self.default_amount,self.min_principal,self.max_principal ))
            if self.default_amount < self.min_principal:
                raise ValidationError(_("principal value range is inconsistent: Default=%s Min=%s Max=%s") % (self.default_amount,self.min_principal,self.max_principal ))
    
    @api.constrains('is_check_by_interest_rate_range','min_interest','max_interest','interest_rate')
    def check_interest_range_value(self):
        super(LoanType, self).check_interest_range_value()
        if self.is_check_by_interest_rate_range and self.interest_rate >0:
            if self.interest_rate > self.max_interest:
                raise ValidationError(_("interest_rate value range is inconsistent: Default=%s Min=%s Max=%s") % (self.interest_rate,self.min_interest,self.max_interest ))
            if self.min_interest > self.interest_rate:
                raise ValidationError(_("interest_rate value range is inconsistent: Default=%s Min=%s Max=%s") % (self.interest_rate,self.min_interest,self.max_interest ))

#     @api.constrains('is_check_by_no_of_payment_range','min_payment_cnt','max_payment_cnt')
#     def check_no_of_payment_range_value(self):
#         if self.is_check_by_no_of_payment_range:
#             if self.min_payment_cnt > self.max_payment_cnt:
#                 raise ValidationError(_("No. of payment value range is inconsistent:  Min=%s Max=%s") % (self.min_payment_cnt,self.max_payment_cnt ))
#     
 
