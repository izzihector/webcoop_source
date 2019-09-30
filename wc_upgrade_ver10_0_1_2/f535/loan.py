
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError ,UserError
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
    is_interest_deduction_first = fields.Boolean("Interest Deduct at Disbursement",readonly=True, 
                                                 states={'draft': [('readonly', False)]},
                                                 help="Select this flag if you deduct total interest at disbursement.(you can select this in case straight loan only)")

    @api.onchange('loan_type_id')
    def oc_loan_type_id(self):
        super(Loan,self).oc_loan_type_id()
        self.is_interest_deduction_first = self.loan_type_id.is_interest_deduction_first
        
          
    @api.onchange('is_interest_epr')
    def onchange_is_interest_epr(self):
        if not self.is_interest_epr:
            self.is_interest_deduction_first = False


    @api.multi
    def move_to_restructured(self):
        restructure = super(Loan,self).move_to_restructured()
        if self.payment_schedule == 'x-days': 
            self.env['wc.loan'].browse(restructure['res_id']).write(
                {'is_interest_deduction_first':self.is_interest_deduction_first})
        return restructure

#     @api.multi
#     def write(self, vals):
#         res = super(Loan, self).write(vals)
#         if 'is_interest_deduction_first' in vals:
#             self.generate_deductions()
#         return res            

#     @api.model
#     def get_deductions(self, loan):
#         deductions = super(Loan, self).get_deductions(loan)
# 
#         if loan.is_interest_deduction_first:
# #         if loan.loan_type_id.is_interest_deduction_first:
#             val = {
#                 'sequence': 999,
#                 'loan_id': loan.id,
#                 'code': 'ADV-INT',
#                 'name': 'Interest Advance Deduction',
#                 'recurring': False,
#                 'net_include': True,
#                 'factor': 0.0,
#                 'amount': 0.0,
#                 'gl_account_id': loan.get_interest_income_account_id(),
#                 }
# 
#             _logger.debug("**gen_deductions: %s", val)
#             deductions.append( (0, False, val.copy()) )
# 
#         return deductions
    
    @api.model
    def get_deductions(self, loan):
        deductions = super(Loan, self).get_deductions(loan)
        loan.recompute_update_advance_interest()
        return deductions


    def calculate_total_interest_for_straight_method(self):
        self.ensure_one()
        loan = self
        if not loan.is_interest_deduction_first or loan.state != 'draft' \
           or loan.date_start==False or loan.date_maturity==False:
            return False
        
        try:
            days_in_year = float(loan.days_in_year)
        except:
            days_in_year = 365.0
        d1 = fields.Datetime.from_string(loan.date_start)
        dend = fields.Datetime.from_string(loan.date_maturity)
        days = (dend - d1).days

        if loan.maturity_period=='months' and loan.payment_schedule in ['half-month','month','quarter','semi-annual','year']:
            tinterest = round(loan.amount * loan.interest_rate * loan.maturity / 1200.0, 2)
        else:
            tinterest = round(loan.amount * loan.interest_rate * days / (days_in_year * 100.0), 2)
        return tinterest

    @api.multi
    def recompute_update_advance_interest(self):
        self.ensure_one()
        loan = self

        if loan.state != 'draft':
            return

        for ded in loan.deduction_ids:
            if ded.code.upper()[:7] == 'ADV-INT':
               ded.unlink()

        if not loan.is_interest_deduction_first:
            return

        #re-calculate total interest
        for ded in loan.deduction_ids:
            if ded.code.upper()[:3] == 'ADV':
                raise UserError(_("Cannot use [ADVx] deduction code if interest deduction is checked."))                        

        interest_total = loan.calculate_total_interest_for_straight_method()
        if interest_total == False:
            return
        
        for line in loan.amortizations:
            line.interest_due = 0.0
        
        val = {
        'sequence': 999,
        'loan_id': loan.id,
        'code': 'ADV-INT',
        'name': 'Interest Advance Deduction',
        'recurring': False,
        'net_include': True,
        'factor': 0.0,
        'amount': interest_total,
        'gl_account_id': loan.get_interest_income_account_id(),
        }
        loan.deduction_ids = [[0, 0, val]]
        

        _logger.debug("**done re-calculate total deduction amount (loan_name=%s ,interest_amount=%s",
            loan.name, interest_total)
      


#     @api.multi
#     def generate_amortization_straight_interest(self):
#         for loan in self:
#             for ded in loan.deduction_ids:
#                 if ded.code.upper()[:7] == 'ADV-INT':
#                     ded.unlink()
#         
#         super(Loan, self).generate_amortization_straight_interest()
# 
#         for loan in self:
#             if not loan.is_interest_deduction_first:
# #             if not loan.loan_type_id.is_interest_deduction_first:
#                 continue
#             if loan.state != 'draft':
#                 continue
#             
#             if loan.is_interest_deduction_first:
# #           if loan.loan_type_id.is_interest_deduction_first:
#                 val = {
#                 'sequence': 999,
#                 'loan_id': loan.id,
#                 'code': 'ADV-INT',
#                 'name': 'Interest Advance Deduction',
#                 'recurring': False,
#                 'net_include': True,
#                 'factor': 0.0,
#                 'amount': 0.0,
#                 'gl_account_id': loan.get_interest_income_account_id(),
#                 }
#                 loan.deduction_ids = [[0, 0, val]]
#             
#             #re-calculate total deduction amount in [ADV] code (supposedly only [ADVxx] is existing
#             ded_total = 0.0
#             adv_interest_record = False
#             for ded in loan.deduction_ids:
#                 if ded.code.upper()[:3] == 'ADV':
#                     if adv_interest_record:
#                         raise UserError(_("Cannot define two advance interest deductions at the same time."))
#                     ded_total += ded.amount
#                     ded.amount = 0.0
#                     adv_interest_record = ded
# 
#             #re-calculate total interest                    
#             interest_total = ded_total
#             for line in loan.amortizations:
#                 interest_total += line.interest_due
#                 line.interest_due = 0.0
#     
#             adv_interest_record.amount = interest_total
# 
#             _logger.debug("**done re-calculate total deduction amount (loan_name=%s ,interest_amount=%s",
#                 loan.name, interest_total)
            
            
            

       