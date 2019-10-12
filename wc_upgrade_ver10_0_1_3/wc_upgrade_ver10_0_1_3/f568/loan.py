
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

    @api.onchange('loan_type_id')
    def oc_loan_type_id(self):
        super(Loan,self).oc_loan_type_id()
        if self.loan_type_id.default_amount>0:
           self.amount = self.loan_type_id.default_amount

       