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

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        required=False, readonly=True, ondelete="set null")



#
