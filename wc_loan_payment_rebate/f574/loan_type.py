# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

#TODO: defined in config
account_number_length = 6


class LoanType(models.Model):
    _inherit = "wc.loan.type"
    
    rebatable_payment_type = fields.Selection([
        ('interest_only', 'interest_only'),
        ('int_penalty', 'int_penalty')],
        'Rebatable for Interest payment only or Interest and Penalty',
        default='interest_only')
    

