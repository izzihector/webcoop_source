# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

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
    _inherit = "wc.loan.type"

    is_interest_epr = fields.Boolean("Straight Interest",
        help="Interest rate is calculated using EPR or straight (not simple interest).")

    round_to_peso = fields.Boolean("Round to Peso",
        help="Payments are rounded to peso.", default=True)

    bulk_principal_payment = fields.Boolean("Bulk Principal Pay",
        help="Pay principal on the last payment.")

    skip_saturday = fields.Boolean("Skip Saturday",
        help="No payment on saturdays.")

    #rate_label = fields.Char(compute="compute_rate_label")

    #@api.depends('is_interest_epr')
    #def compute_rate_label(self):
    #    for l in self:
    #        l.rate_label = '% per year'
    #        #if l.is_interest_epr:
    #        #    l.rate_label = '% per period'
    #        #else:
    #        #    l.rate_label = '% per year'



#
