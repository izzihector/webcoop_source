# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanType(models.Model):
    _inherit = "wc.loan.type"
    
    cash_disbursement_limit =fields.Float("Cash Disbursement Limit", help="if over this amount, disbursement will be done by check .")
    is_interest_deduction_first = fields.Boolean("Interest Deduct at Disbursement",help="Select this flag if you deduct total interest at disbursement.(you can select this in case straight loan only)")
    

 
