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
    _inherit = "wc.loan.type"
    payment_schedule = fields.Selection(selection_add=[('x-days', 'every x-days')])
    payment_schedule_xdays = fields.Integer('days')


    @api.constrains('payment_schedule_xdays')
    def validate_payment_schedule_xdays(self):
        for rec in self:
            if rec.payment_schedule == 'x-days':
                if rec.payment_schedule_xdays == 1:
                    raise ValidationError(_("Please use daily schedule in case of every 1 days schedule"))
                if rec.payment_schedule_xdays < 1:
                    raise ValidationError(_("Please input number over 1 day if payment schedule is x-days"))                    
            return True
        
    @api.onchange('payment_schedule')
    def onchange_payment_schedule(self):
        if self.payment_schedule != 'x-days':
            self.payment_schedule_xdays = False
            
