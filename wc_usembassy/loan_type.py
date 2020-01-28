# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
EPS = 0.00001

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

#add fields and  for [f600]

class Deductions(models.Model):
    _inherit = "wc.loan.type"
        

    @api.constrains('deduction_ids','deduction_ids.code','deduction_ids.deduction_type')
    def validate_code_constrains(self):
        for loan_type in self:
            check_list1 = []
            check_list2 = []
            
            for ded in loan_type.deduction_ids:
                if ded.deduction_type in ['sa','lgf']:
                    if ded.deduction_type in check_list1:
                        raise ValidationError(_("Cannot set multiple [%s] deduction type's deduction items" % (ded.deduction_type)))
                    else:
                        check_list1.append(ded.deduction_type)
                else:
                    if ded.code in check_list2:
                        raise ValidationError(_("Cannot set same code in deduction items."))
                    else:
                        check_list2.append(ded.code)
