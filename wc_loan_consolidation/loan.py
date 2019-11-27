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

class Loan(models.Model):
    _inherit = "wc.loan"
    #In original module, 1 loan restructure to 1 lone , now x loans restructure to 1 loan 
    #so need to change restructured_from fields to one2many . 
    #For lessen the affect of this fixing ,simply add one2many field with holding original field
    restructured_from_ids = fields.One2many('wc.loan','restructured_to_id',
                                           string='Restructured From', readonly=True)
    is_restructured_target_loan = fields.Boolean(compute='compute_is_restructured_target')
    is_allowed_restructure = fields.Boolean(compute='compute_is_allowed_restructure')
    
    @api.depends('is_restructured_target_loan','company_id.is_allow_restructure_again')
    def compute_is_allowed_restructure(self):
        if self.is_restructured_target_loan:
            if self.company_id.is_allow_restructure_again:
                self.is_allowed_restructure = True
            else:
                self.is_allowed_restructure = False
        else:
            self.is_allowed_restructure = True
            

    @api.depends('restructured_from_ids')
    def compute_is_restructured_target(self):
        if len(self.restructured_from_ids) >= 1:
            self.is_restructured_target_loan = True
        else:
            self.is_restructured_target_loan = False