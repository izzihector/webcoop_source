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

#not yet implemented

class Company(models.Model):
    _inherit = "res.company"

    branch_code = fields.Char("Branch Code", default="000")
    name = fields.Char(string="Branch Name")

    @api.model
    def get_open_date(self):
        self.ensure_one()
        return fields.Date.context_today(self)

    @api.model
    def get_last_closed_date(self):
        self.ensure_one()
        return fields.Date.context_today(self)
