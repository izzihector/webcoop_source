
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

    @api.onchange('loan_type_id')
    def oc_loan_type_id(self):
        super(Loan,self).oc_loan_type_id()
        self.is_interest_deduction_first = self.loan_type_id.is_interest_deduction_first
        
          
    @api.onchange('is_interest_epr')
    def onchange_is_interest_epr(self):
        #erase previours onchange action, because upfront interest should be applied on declining loan also
        pass
    
    #Todo:add onchange function for checking unchecking of fixed amount flag in case of decline and upfront interest
    @api.onchange('is_interest_epr','is_interest_deduction_first')
    def onchange_is_interest_deduction_first(self):
        self.ensure_one()
        if self.is_interest_deduction_first:
            self.is_fixed_payment_amount = False

#refactoring 20191101    
    @api.multi
    def calculate_total_interest_for_simple_method(self, round_to_peso=True):
        
        self.ensure_one()
        loan = self
        if not loan.is_interest_deduction_first or loan.state != 'draft' \
           or loan.date_start==False or loan.date_maturity==False:
            return False

#refactor get_loan_schedules_for_deminishing module    
#         tbalance = loan.amount
#         try:
#             days_in_year = float(loan.days_in_year)
#         except:
#             days_in_year = 365.0
# 
#         d1 = fields.Datetime.from_string(loan.date_start)
#         d0 = d1
#         dend = fields.Datetime.from_string(loan.date_maturity)
#         i = 1
# 
#         payments = loan.term_payments
#         principal_due = 0.0
# 
#         default_principal_due = round(loan.amount / payments, 2)
# 
#         if loan.interest_rate == 0.0:
#             c = default_principal_due
#         else:
#             d2, days = self.get_next_due(d1, loan.payment_schedule, i, d0, loan=loan)
#             r = loan.interest_rate * days / (days_in_year * 100.0)
#             c = loan.amount * r / (1.0 - 1.0 / ((1+r)**payments))
#             if round_to_peso:
#                 c = math.ceil(c)
# 
#         interest_total = 0
#         
#         for i in range(1, loan.term_payments):
#             d2, dx = self.get_next_due(d1, loan.payment_schedule, i, d0, loan=loan)
#             days = (d2 - d1).days
#             #interest_due = round(tbalance * loan.interest_rate * days / (days_in_year * 100.0), 2)
#             interest_due = loan.compute_interest(
#                 tbalance,
#                 d1.strftime(DF),
#                 d2.strftime(DF)
#             )
#             #add interest_due of each schedule on interest_total
#             interest_total += interest_due
#             principal_due = self.compute_principal_due(default_principal_due, interest_due, c)
# 
#             tbalance = tbalance - principal_due
#             d0 = d1
#             d1 = d2
#             i += 1
# 
#         days = (dend - d1).days
#         interest_due = loan.compute_interest(
#             tbalance,
#             d1.strftime(DF),
#             dend.strftime(DF)
#         )
#         
#         #add interest_due of last schedule on interest_total
#         interest_total += interest_due
#         return interest_total        
        lines = self.get_loan_schedules_for_deminishing(round_to_peso)
        interest_total = 0 
        for line in lines:
            interest_total += line['interest_due']
        
        return interest_total


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

        #f535_2's modification part start
        if loan.is_interest_epr:
            interest_total = loan.calculate_total_interest_for_straight_method()
        else:
            interest_total = loan.calculate_total_interest_for_simple_method(loan.loan_type_id.round_to_peso)
        #f535_2's modification part end

        if interest_total == False or interest_total == 0:
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
      
    #overwrite for f567
    @api.multi
    def generate_schedule(self):
        for loan in self:
            if loan.state=='draft':
                ndate = self.get_first_open_date()
                if loan.date!=ndate:
                    if loan.editable_date and loan.date:
                        if loan.date>=self.env.user.company_id.start_date:
                            loan.date = ndate
                            #raise ValidationError(_("Approval date should be equal to open posting date or prior to beginning date."))
                    else:
                        loan.date = ndate
                _logger.debug("gen sched: date=%s", loan.date)        

            if loan.is_interest_epr:
                loan.generate_amortization_straight_interest()
#                 loan.term_payments = len(loan.amortizations)
                if loan.is_interest_deduction_first:
                    loan.recompute_update_advance_interest()
            else:
#                 super(Loan, loan).generate_amortization_simple_interest(round_to_peso=True)
                loan.generate_amortization_simple_interest(round_to_peso=True)
                #f567
                if loan.is_interest_deduction_first:
                    loan.recompute_update_advance_interest()
       