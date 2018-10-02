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

class Users(models.Model):
    _inherit = "res.users"

    @api.onchange('login')
    def on_change_login(self):
        if self.login:
            if tools.single_email_re.match(self.login):
                self.email = self.login
            else:
                self.email = "%s@example.com" % self.login
