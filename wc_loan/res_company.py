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

    cash_account_id = fields.Many2one('account.account', string='Cash', ondelete="restrict")
    check_account_id = fields.Many2one('account.account', string='Bank', ondelete="restrict")
    #cash_receipt_journal_id = fields.Many2one('account.journal', string='Cash Receitp Journal', ondelete="restrict")
