
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
    
    #fix b575
    @api.one
    @api.constrains('deduction_ids','deduction_ids.amount','amount')
    def validate_net_amount(self):
        if self.net_amount <0:
            raise ValidationError(_("This loan cannot be created because amount is less than amount of deduction."))
