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

    #20200117 add start for usembassy's LGF feature
    cbu_balance = fields.Float('Paid UP Capital(CBU balance)'
                        ,compute='compute_cbu_loan_balance',store=True)
#     cbu_balance_att = fields.Float('Paid UP Capital(CBU balance)')
    
    loanable_base_on_cbu = fields.Float('Loanable Base on Capital Investment'
                        ,compute="compute_cbu_loan_balance",store=True)
#     loanable_base_on_cbu_att = fields.Float('Loanable Base on Capital Investment')
    

###20200527 change autocalculaton to usual input field (according to client request)
    outstanding_loan_amount = fields.Float('Outstanding Loans', readonly=True, states={'draft': [('readonly', False)]})
#    outstanding_loan_amount = fields.Float('Outstanding Loans'
#                        ,compute="compute_cbu_loan_balance",store=True)
#     outstanding_loan_amount_att = fields.Float('Outstanding Loans')


    loanable_amount = fields.Float('Loanable Amount')
#    loanable_amount = fields.Float('Loanable Amount'
#                        ,compute="compute_cbu_loan_balance",store=True)
#     loanable_amount_att = fields.Float('Loanable Amount')

    uncollateralized_amount = fields.Float(compute="compute_cbu_loan_balance")

    #20200122 add for rebate consolidate
    consolidate_rebate_ids = fields.One2many('wc.loan.payment.rebate', 'rebate_target_consolidated_loan_id')
    consolidate_rebate_ref_count = fields.Integer(compute="compute_consolidate_rebate_cnt")
#     @api.depends('amount','uncollateralized_amount','cbu_balance')
#     def compute_uncollatelized_loan(self):
#         for loan in self:
#             a = self.amount - self.cbu_balance
#             self.uncollateralized_amount = a if a >0 else 0

    ##20200527 
    @api.onchange('outstanding_loan_amount')
    def onchange_outstanding(self):
        for loan in self:
            loan.compute_cbu_loan_balance()
            
    
        
    @api.depends('consolidate_rebate_ids')
    def compute_consolidate_rebate_cnt(self):
        for loan in self:
            loan.consolidate_rebate_ref_count = len(loan.consolidate_rebate_ids)
    
    
    @api.depends('member_id','amount')
    def compute_cbu_loan_balance(self):
        for loan in self:
            if loan.member_id:
                src_member_id = loan.member_id.id
                cbus = self.env['wc.account'].search([('account_type','=','cbu'),('member_id','=',src_member_id)])
                #####20200527
                #oloans = self.env['wc.loan'].search([('member_id','=',src_member_id),('state','in',['approved','past-due'])])
                cbu_bal = 0
                oloan_bal = 0
                
                ##bug fix 20200604
                bal =0
                
                if len(cbus) > 0:
                    bal = cbus[0].balance
                #####20200527
#                if len(oloans) > 0:
#                    oloan_bal = sum(oloan.principal_balance for oloan in oloans)
                    
                loan.cbu_balance = bal if bal > 0 else 0
                loan.loanable_base_on_cbu = bal*3 if bal>0 else 0
                
                #####20200527
#                loan.outstanding_loan_amount = oloan_bal if oloan_bal >0 else 0
                if not loan.outstanding_loan_amount:
                    loan.outstanding_loan_amount = 0
                
                loan.loanable_amount = (bal*3 - loan.outstanding_loan_amount) if bal*3>loan.outstanding_loan_amount else 0

                a = loan.outstanding_loan_amount / 3 + loan.amount - loan.cbu_balance
                loan.uncollateralized_amount = a if a >0 else 0

    #20200117 add end for usembassy's LGF feature


    #20200120 add start for usembassy's LGF feature
    @api.model
    def get_deductions(self, loan):
        deductions = super(Loan, self).get_deductions(loan)
        for ded in deductions:
            val = ded[2]
            if val['code'] == 'SA' and val['deposit_account_id']:
                account_id = self.env['wc.account'].browse(val['deposit_account_id'])
                if account_id.account_type_id.is_lgf:
                    #logic for get lgf deduction amount
                    #variables
                    uncol_amount = 0.0
                    if loan.uncollateralized_amount > 0:
                        uncol_amount = loan.uncollateralized_amount
                    
                    #get lgf balance as of now
                    lgf_bal = account_id.balance
                    acc_type = account_id.account_type_id
                    if acc_type.lgf_rate_change_balance > lgf_bal:
                        lgf_rate = account_id.account_type_id.lgf_rate_1 / 100
                    elif acc_type.lgf_rate_change_balance <= lgf_bal:
                        lgf_rate = account_id.account_type_id.lgf_rate_2 / 100
                    else:
                        raise ValidationError(_("There is no rate in the selected LGF saving account.Configure its account type master correctly."))

                    lgf_amount = uncol_amount * lgf_rate
                    
                    val['amount'] = lgf_amount

        return deductions
    #20200120 add end for usembassy's LGF feature
    
    #20200121 add for usembassy's rebate amount calculation
    #return unbilled count , and total count of the loan schedule , at certain date
    def get_unbilled_count_at_date(self,date=False):
        self.ensure_one()
        loan = self
        
        #get total count of schedule
        
        unbilled_cnt = 0
        
        for a in loan.amortizations:
            if a.date_due > date and date <= loan.date_maturity:
                unbilled_cnt +=1

            
#                 
#                 
#             unbill = loan.amortizations.search([('date_due','>',date)])
#             unbilled_cnt = len(unbill)
        
        return unbilled_cnt
    
    #return paid interest(interest amount in deduction(for usemb only), 
    def get_rebate_amount_at_date(self,date=False):
        self.ensure_one()
        loan = self
        
        #variables setting
        if not (loan.amount >0 and loan.term_payments > 0):
            raise ValidationError(_("amount or payment terms of loan [%] is not set") % (loan.name))

        amt = loan.amount
        terms = loan.term_payments
        allotment = amt / terms
        int_per_term = 0.0025

        unbilled_cnt = loan.get_unbilled_count_at_date(date)
        if (unbilled_cnt >terms):
            raise ValidationError(_("amortization schedule or rebate date is not correct(loan [%])") % (loan.name))

        paid_terms = terms - unbilled_cnt
        #calculation
        va1_a = allotment * (terms + 1) * terms * int_per_term
        val_b = allotment * (paid_terms + 1) * paid_terms * int_per_term
        rebate_amt = va1_a-val_b
        return va1_a, val_b, rebate_amt
                
        