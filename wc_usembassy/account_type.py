# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

account_number_length = 6

class AccountType(models.Model):
    _inherit = "wc.account.type"
    #add for usembassy's special saving interest calculation style
    interest_rate = fields.Float(default = "0.00")

    #20200117 add for usembassy's loan guarantee fund type saving account-->
    is_lgf = fields.Boolean('LGF?')
    lgf_rate_1 = fields.Float('LGF Rate(%) less than threshold',help='LGF Rate if this account balance is less than Rate Change Balance.')
    lgf_rate_2 = fields.Float('LGF Rate(%) equal/more than threshold',help='LGF Rate if over than or equal to Rate Change Balance.')
    lgf_rate_change_balance = fields.Float('threshold(LGF Balance for rate change)')
    
    
    @api.onchange('category','is_lgf')
    def onchange_cat_is_lgf(self):
        for acc in self:
            if acc.category != 'sa' or not acc.is_lgf:
                acc.lgf_rate_1 = False
                acc.lgf_rate_2 = False
                acc.lgf_rate_change_balance = False
            
        
                

