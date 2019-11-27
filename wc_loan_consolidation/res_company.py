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

    is_allow_restructure_again = fields.Boolean('Allow loan restructure for restructured loan(This is not recommended)',
                                  help="Tap on , in case your coop allow restructure or consolidate loan for restructured loan again.But this is not recommended.")
    
