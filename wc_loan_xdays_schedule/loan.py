
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
#from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _inherit = "wc.loan"
    
    payment_schedule = fields.Selection(selection_add=[('x-days', 'every x-days')])
    payment_schedule_xdays = fields.Integer('days',track_visibility='onchange', 
        readonly=True, states={'draft': [('readonly', False)]})
    
    
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
            
    @api.onchange('loan_type_id')
    def oc_loan_type_id(self):
        super(Loan,self).oc_loan_type_id()
        self.payment_schedule_xdays = self.loan_type_id.payment_schedule_xdays

    @api.multi
    @api.depends('payment_schedule','date_start')
    def compute_date_first_due(self):
        for r in self:
            if r.date_start == False:
               return            
            if r.payment_schedule == 'x-days':
                mdate = fields.Datetime.from_string(r.date_start)
                mdate, days = self.get_next_due(mdate, r.payment_schedule, 1, mdate, loan=r)
                if mdate:
                    r.date_first_due = mdate.strftime(DF)
            else:
                super(Loan,r).compute_date_first_due()

    @api.multi
    @api.depends(
        'maturity',
        'maturity_period',
        'date_start',
        'payment_schedule',
        'payment_schedule_xdays'
        #'is_360_day_year'
    )
    def compute_date_maturity(self):
        for rec in self:
            if rec.date_start == False or rec.maturity_period == False :
                rec.date_maturity = False
                rec.term_payments = False
                return
            
            super(Loan,rec).compute_date_maturity()
            if rec.payment_schedule == 'x-days' and rec.payment_schedule_xdays > 0:
                rec.compute_date_first_due()
                dt0 = fields.Datetime.from_string(rec.date_start)
                dt = fields.Datetime.from_string(rec.date_maturity)
                days = (dt - dt0).days

                n = math.ceil(days/float(rec.payment_schedule_xdays))
                rec.term_payments = n

    @api.multi
    def import_approve(self):
        for r in self:
            if r.payment_schedule =='x-days':
                r.payment_schedule_xdays = r.loan_type_id.payment_schedule_xdays
                super(Loan,r).import_approve()

    @api.multi
    def move_to_restructured(self):
        restructure = super(Loan,self).move_to_restructured()
        if self.payment_schedule == 'x-days': 
            self.env['wc.loan'].browse(restructure['res_id']).write(
                {'payment_schedule_xdays':self.payment_schedule_xdays})
        return restructure
    

    @api.model
    def get_next_due(self, d1, payment_schedule, i=0, d0=None, loan=False):
        
        if payment_schedule == 'x-days':
            d2 = False
            days = False
            if loan and loan.payment_schedule_xdays:
                d2 = d1 + relativedelta(days=loan.payment_schedule_xdays)
                days = loan.payment_schedule_xdays
            return d2, days
        else:
            return super(Loan,self).get_next_due(d1, payment_schedule, i, d0, loan)
            

#
