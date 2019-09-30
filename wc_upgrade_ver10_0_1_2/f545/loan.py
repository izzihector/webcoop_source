
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
    
    @api.onchange('amount')
    def oc_amount(self):
       self.ensure_one()
       cash_limit = self.loan_type_id.cash_disbursement_limit
       if cash_limit and cash_limit >= 0:
           if self.amount>cash_limit:
              self.is_check_payment = True
           else:
              self.is_check_payment = False
           
           