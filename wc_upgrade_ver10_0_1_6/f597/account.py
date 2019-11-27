# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import time

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Account(models.Model):
    _inherit = "wc.account"

    def get_dep_account_id(self):
        self.ensure_one()
        acc_type=self.account_type_id
        
        return acc_type.get_dep_account_id()
        #
