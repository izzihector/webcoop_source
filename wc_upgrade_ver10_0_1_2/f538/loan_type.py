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
    is_check_by_principal_range = fields.Boolean("Inputtable principal range",default=False,help="If checked here and set min and max value, you can restrict principal amount between min and max value.")
    is_check_by_interest_rate_range = fields.Boolean("Inputtable interest rate range",default=False,help="If checked here and set min and max value, you can interest rate between min and max value.")
    is_check_by_no_of_payment_range = fields.Boolean("Inputtable range of number of repayments ",default=False,help="If checked, inputtable range of principal amount can be set")

    min_principal = fields.Float(string="Min")
    max_principal = fields.Float(string="Max")
    min_interest = fields.Float(string="Min")
    max_interest = fields.Float(string="Max")
    min_payment_cnt = fields.Integer(string="Min")
    max_payment_cnt = fields.Integer(string="Max")
    
    @api.constrains('is_check_by_principal_range','min_principal','max_principal')
    def check_principal_range_value(self):
        if self.is_check_by_principal_range:
            if self.min_principal > self.max_principal:
                raise ValidationError(_("principal value range is inconsistent:  Min=%s Max=%s") % (self.min_principal,self.max_principal ))
    
    @api.constrains('is_check_by_interest_rate_range','min_interest','max_interest')
    def check_interest_range_value(self):
        if self.is_check_by_interest_rate_range:
            if self.min_interest > self.max_interest:
                raise ValidationError(_("interest_rate value range is inconsistent:  Min=%s Max=%s") % (self.min_interest,self.max_interest ))

    @api.constrains('is_check_by_no_of_payment_range','min_payment_cnt','max_payment_cnt')
    def check_no_of_payment_range_value(self):
        if self.is_check_by_no_of_payment_range:
            if self.min_payment_cnt > self.max_payment_cnt:
                raise ValidationError(_("No. of payment value range is inconsistent:  Min=%s Max=%s") % (self.min_payment_cnt,self.max_payment_cnt ))
    
    @api.onchange('is_check_by_principal_range')
    def onchange_is_check_by_principal_range(self):
        if not self.is_check_by_principal_range:
            self.min_principal = False
            self.max_principal = False
            
    @api.onchange('is_check_by_interest_rate_range')
    def onchange_is_check_by_interest_rate(self):
        if not self.is_check_by_interest_rate_range:
            self.min_interest = False
            self.max_interest = False            

    @api.onchange('is_check_by_no_of_payment_range')
    def onchange_is_check_by_no_of_payment(self):
        if not self.is_check_by_no_of_payment_range:
            self.min_payment_cnt = False
            self.max_payment_cnt = False       
    
    
 
