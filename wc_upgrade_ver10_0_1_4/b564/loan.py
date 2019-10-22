
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
from pickle import FALSE
#from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _inherit = "wc.loan"
    
    
    @api.depends(
        'date_start',
        'state',
        'details',
        'details.state',
        'details.date_due',
        'details.principal_due',
        'details.principal_paid',
        'details.interest_due',
        'details.interest_paid',
        'details.penalty',
        'details.adjustment',
        'details.penalty_paid',
        'details.others_due',
        'details.others_paid',
        'amortizations',
        'amortizations.state',
        'amortizations.interest_due',
        'amortizations.date_due',
    )
    def _compute_totals2(self):
        for loan in self:
            super(Loan,self)._compute_totals2()
            if loan.state == "restructured":
                loan.principal_balance = 0
                loan.interest_balance = 0
                loan.total_balance = 0
