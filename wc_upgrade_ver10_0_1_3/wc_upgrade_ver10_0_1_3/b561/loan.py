
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
from pickle import FALSE
#from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _inherit = "wc.loan"
    

    #overwrite this module because of the bug of b561
    #if restructured loan, unlink restructured 
    def unlink_recreate_deduction(self):
        self.ensure_one()
        loan = self
#         if loan.restructured_from_id:
#             raise UserError(_("This is restructured loan , you need to manually add deduction items."))
        
        if loan.state=='draft' and loan.loan_type_id and loan.amount>0.0:
#            loan.deduction_ids.unlink()
            for ded in loan.deduction_ids:
                #do not delete deductions for restructured loans
                if ded.code not in ['PCP','INT','PEN']:
                    ded.unlink()
            deductions = loan.get_deductions(loan)
            if deductions:
                _logger.debug("**all_deductions: %s", deductions)
                loan.deduction_ids = deductions
 
    #overwrite this module because of the bug of b561 and xdays schedule
    #system error happens when create restructured if xdays schedule
    @api.multi
    def move_to_restructured(self):
        self.ensure_one()
        #self.check_gl_accounts_setup()
 
        pcp_amount = self.principal_balance
        int_amount = 0.0
        penalty_amount = 0.0
        for d in self.details:
            int_amount += d.interest_due - d.interest_paid
            penalty_amount += d.penalty + d.adjustment - d.penalty_paid
 
        lines = []
 
        if pcp_amount:
            val = {
                'sequence': 1,
                'code': 'PCP',
                'name': 'Restructured Principal',
                'recurring': False,
                'net_include': True,
                'factor': 0.0,
                'amount': pcp_amount,
                'gl_account_id': self.get_ar_account_id(),
            }
            lines.append( (0, False, val) )
 
        if int_amount:
            val = {
                'sequence': 2,
                'code': 'INT',
                'name': 'Restructured Interest',
                'recurring': False,
                'net_include': True,
                'factor': 0.0,
                'amount': int_amount,
                'gl_account_id': self.get_interest_income_account_id(),
            }
            lines.append( (0, False, val) )
 
        if penalty_amount:
            val = {
                'sequence': 3,
                'code': 'PEN',
                'name': 'Restructured Penalty',
                'recurring': False,
                'net_include': True,
                'factor': 0.0,
                'amount': penalty_amount,
                'gl_account_id': self.company_id.penalty_account_id.id,
            }
            lines.append( (0, False, val) )
        #modify start b561  
        res = self.create({
            'restructured_from_id': self.id,
            'loan_type_id': self.loan_type_id.id,
            'maturity': self.maturity,
            'payment_schedule': self.payment_schedule,
            'term_payments': self.term_payments,
            'is_fixed_payment_amount': self.is_fixed_payment_amount,
            'interest_rate': self.interest_rate,
            'amount': self.amount,
            'term_payments': self.term_payments,
            'company_id': self.company_id.id,
            'member_id': self.member_id.id,
            'comaker_ids': self.comaker_ids,
            'deduction_ids': lines,
            'payment_schedule_xdays': self.payment_schedule_xdays,#add this line f561
        })
        #modify end b561  
 
        self.restructured_to_id = res.id
        self.state = 'restructured'
 
        view_id = self.env.ref('wc_loan.view_loan').id
        context = self._context.copy()
        #context.update({
        #    'default_restructured_to_id': self.id,
        #})
        return {
            'res_id':res.id,
            'name':'New Loan',
            'view_type':'form',
            'view_mode':'form',
            'views' : [(view_id,'form')],
            'res_model':'wc.loan',
            'view_id':view_id,
            'type':'ir.actions.act_window',
            'target':'current',
            #'target':'new',
            'context':context,
        }



