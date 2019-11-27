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

    
    date_parameter_for_cbu_balance = fields.Integer('Month date for CBU Balance',
                                  help="""
                                  This is technical field for calculation of dividend in case of dividend patern1 module is installed.
                                  set date for share capital monthly balance calculation.If you set 7 here, 
                                  balance of Jan7 is regarded as January's share capital balance.
                                  (meaning deposing on 8th date onward will be reflect on next month's balance.
                                  """)
    
    @api.constrains('date_parameter_for_cbu_balance')
    def check_dividend_parameter(self):
        if self.date_parameter_for_cbu_balance:
            if not (self.date_parameter_for_cbu_balance >= 1 and self.date_parameter_for_cbu_balance <=31):
                raise ValidationError(_("Please set between 1 and 31 on [Month date for CBU Balance]"))
            
            
            