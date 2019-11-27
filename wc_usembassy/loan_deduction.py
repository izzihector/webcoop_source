
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

class LoanDeduction(models.Model):
    _inherit = "wc.loan.deduction"
    

            