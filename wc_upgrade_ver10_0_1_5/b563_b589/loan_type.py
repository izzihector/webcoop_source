# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanType(models.Model):
    _inherit = "wc.loan.type.deduction"
    
#need to avoid interest and     
    @api.multi
    @api.constrains('code')
    def check_deduction_code(self):
        for r in self:
            if r.code in ['PCP','INT','PEN','ADV-INT']:
                raise ValidationError(_("Please don't use PCP,INT,PEN,ADV-INT as deduction code."))
 
