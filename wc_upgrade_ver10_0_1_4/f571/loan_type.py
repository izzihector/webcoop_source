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
    
    term_payments_for_input = fields.Integer("Payment Count")

    
    schedule_making_type = fields.Selection(
        [('periods', 'By Maturity Period'),('count', 'By Payment Count')],
        string='Schedule Generate Type',
        help="""
        Select [By Maturity Period] in case making schedule from maturity period and payment scheudle.
        Select [By Payment Count] in case you want to make schedule from payment schedule and count of payment.
        You cannot select [By Term] ,in case of payment schedule is [days][half-month][lumpsum].
        """,
        default ="periods")
    
    
            
#     @api.onchange('term_payments_for_input','schedule_making_type')
#     def oc_term_payments_for_input(self):
#         for rec in self:
#             self.compute_date_maturity_from_inputterm()
# 
#         
        
        
        
    def compute_date_maturity_from_inputterm(self):
        rec = self
        
        if rec.schedule_making_type == "count":
            if rec.payment_schedule:
                if rec.payment_schedule == "day" or \
                    rec.payment_schedule == "half-month" or \
                    rec.payment_schedule == "lumpsum":
                    return "force_to_period",False,False
                
                t = rec.term_payments_for_input
                if (rec.payment_schedule=='day'):
                    raise Warning(_("You cannot change this ,in case of day schedule."))
                elif (rec.payment_schedule=='week'):
                    mat = t
                    peri = "weeks"
                elif (rec.payment_schedule=='half-month'):
                    raise Warning(_("You cannot change this ,in case of day semi-monthly schedule."))
                elif (rec.payment_schedule=='15-days'):
                    mat = t * 15
                    peri = "days"
                elif (rec.payment_schedule=='month'):
                    mat = t
                    peri = "months"
                elif (rec.payment_schedule=='30-days'):
                    mat = t * 30
                    peri = "days"
                elif (rec.payment_schedule=='quarter'):
                    mat = t * 3
                    peri = "months"
                elif (rec.payment_schedule=='semi-annual'):
                    mat = t * 6
                    peri = "months"
                elif (rec.payment_schedule=='year'):
                    mat = t * 12
                    peri = "months"
                elif (rec.payment_schedule=='x-days'):
                    mat = t * rec.payment_schedule_xdays
                    peri = "days"

                return "change",mat,peri
            else:
                return "stay",False,False
        elif rec.schedule_making_type == "periods":
            return "periods",False,False
        else:
            return False,False,False


    @api.onchange('term_payments_for_input',
                  'payment_schedule',
                  'payment_schedule_xdays',
                  'schedule_making_type')
    def oc_for_schedule_making_type(self):
        for rec in self:
            result,mat,peri = rec.compute_date_maturity_from_inputterm()
            if result=="stay":
                continue
            elif result=="change":
                rec.maturity = mat
                rec.maturity_period = peri
            elif result == "force_to_period":
                return {'value':{'schedule_making_type':'periods',
                                 'term_payments_for_input':False}}
            else:
                rec.term_payments_for_input = False


                