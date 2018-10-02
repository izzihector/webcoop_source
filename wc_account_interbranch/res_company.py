# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Company(models.Model):
    _inherit = "res.company"

    ib_payable_account_id = fields.Many2one('account.account', string='Interbranch Payable', ondelete="restrict")
    ib_receivable_account_id = fields.Many2one('account.account', string='Interbranch Receivable', ondelete="restrict")



#
