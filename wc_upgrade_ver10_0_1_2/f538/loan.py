
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError ,UserError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
#from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _inherit = "wc.loan"

 
    @api.constrains('amount')
    def amount_range_check(self):
        for loan in self:
            ltype = loan.loan_type_id
            if ltype.is_check_by_principal_range:
                if loan.amount < ltype.min_principal or loan.amount > ltype.max_principal:
                    raise ValidationError(_("You can input as loan amount between %s and % s") % (ltype.min_principal,ltype.max_principal ))
                    
    @api.constrains('interest_rate')
    def interest_rate_range_check(self):
        for loan in self:
            ltype = loan.loan_type_id
            if ltype.is_check_by_interest_rate_range:
                if loan.interest_rate < ltype.min_interest or loan.interest_rate > ltype.max_interest:
                    raise ValidationError(_("You can input as interest rate between %s and % s") % (ltype.min_interest,ltype.max_interest ))

#    @api.constrains('term_payments','maturity')
    @api.constrains('maturity')
    def term_payments_range_check(self):
        for loan in self:
            ltype = loan.loan_type_id
            if ltype.is_check_by_no_of_payment_range:
                if loan.term_payments < ltype.min_payment_cnt or loan.term_payments > ltype.max_payment_cnt:
                    raise ValidationError(_("Please adjust schedule so that No of payments become between %s and % s") % (ltype.min_payment_cnt,ltype.max_payment_cnt ))

       