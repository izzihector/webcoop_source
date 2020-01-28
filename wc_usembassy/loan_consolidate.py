# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
from data.webcoop.wc_account.ctd import num2amt

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanConsolidateLine(models.TransientModel):
    _inherit = "wc.loan.consolidate.line"
    
    loan_id = fields.Many2one('wc.loan')

    #20200127 del
#     rebate_amount = fields.Float(compute="get_total_rebate",store=True)
    rebate_amount = fields.Float()

    #20200127     del
#     @api.depends('loan_id','header_id.date')
#     def get_total_rebate(self):
#         for line in self:
#             if line.loan_id and line.header_id.date:
#                 loan = line.loan_id
#                 a,b,rebate_amt = loan.get_rebate_amount_at_date(line.header_id.date)
#                 line.rebate_amount_tmp = rebate_amt

    


class LoanConsolidate(models.TransientModel):
    _inherit = "wc.loan.consolidate"
    
    total_rebate = fields.Float(compute="get_total_rebate")
    deb_gl_account_id = fields.Many2one('account.account',required=True,
                                    default=lambda self:self._get_default_account(), 
                                    string='GL Account(debit)',help="set account title for the rebate (this account reflects on debit account ,credit side is cash account anytime.)", ondelete="set null")
    rebate_memo = fields.Text('rebate memo')
    
    @api.model
    def _get_default_account(self):
        company_id = self.env.user.company_id
        return company_id.loan_payment_debate_account_id

    @api.depends('line_ids')
    def get_total_rebate(self):
        for rebate in self:
            amt = 0.0
            for line in rebate.line_ids:
                amt += line.rebate_amount
            rebate.total_rebate = amt


    #overwrite
    @api.multi
    def move_to_consolidate_restructured(self):
        self.ensure_one()
        int_amount = 0.0
        penalty_amount = 0.0

        lines = []
        n = 0
        
        #20200127 add s
        loan_list=[]
        rebate_list=[]
        #20200127 add end
        
        for r in self.line_ids:
            #20200122 mod
#             loan = self.env['wc.loan'].browse(r.loan_id)
            loan = r.loan_id
            
            #check if the company allow restructure
            if not loan.is_allowed_restructure:
                raise UserError(_("Cannot restructure this loan [%s]. This loan may be already restructured. If you allow second term restructure, modify company setting.") % (loan.name))

            #20200127 add start :create rebate on original loan first
            if r.rebate_amount > 0:
                res2 = self.env['wc.loan.payment.rebate'].create({
                        'name': 'Rebate at consolidate',
                        'loan_id': loan.id,
                        'date': self.date,
                        'amount':r.rebate_amount,
                        'note':'This rebate is paid back in consolidated loan by decreading of its consolidated loan deduction',
                        'is_rebate_to_member_account': False,
                        'is_rebate_at_consolidation': True,
                        'deb_gl_account_id':self.deb_gl_account_id.id
                })
                res2.confirm_payment_rebate()
                rebate_list.append(res2)            
            #20200127 add end

            int_amount = 0.0
            penalty_amount = 0.0
            pcp_amount = loan.principal_balance
            for d in loan.details:
                int_amount += d.interest_due - d.interest_paid
                penalty_amount += d.penalty + d.adjustment - d.penalty_paid
 
            if pcp_amount:
                val = {
                    'sequence': n+1,
                    'code': 'PCP',
                    'name': 'Restructured Principal(original loan=[%s])' % loan.name,
                    'recurring': False,
                    'net_include': True,
                    'factor': 0.0,
                    'amount': pcp_amount,
                    'gl_account_id': loan.get_ar_account_id(),
                }
                lines.append( (0, False, val) )
            if int_amount:
                val = {
                    'sequence': n+1,
                    'code': 'INT',
                    'name': 'Restructured Interest(original loan=[%s])' % loan.name,
                    'recurring': False,
                    'net_include': True,
                    'factor': 0.0,
                    'amount': int_amount,
                    'gl_account_id': loan.get_interest_income_account_id(),
                }
                lines.append( (0, False, val) )
            if penalty_amount:
                val = {
                    'sequence': n+1,
                    'code': 'PEN',
                    'name': 'Restructured Penalty(original loan=[%s])' % loan.name,
                    'recurring': False,
                    'net_include': True,
                    'factor': 0.0,
                    'amount': penalty_amount,
                    #fix for bug fouond at 20191125 
    #                 'gl_account_id': self.company_id.penalty_account_id.id,
                    'gl_account_id': loan.get_penalty_account_id(),
                }
                lines.append( (0, False, val) )

            #add start 20200127 update state to restructured
            loan.write({'state':'restructured'})
            loan_list.append(loan)
            #add end 20200127

        #
        res = self.copy_and_create_restructured_loan(lines)
        
        #20200127 add s
        for loan in loan_list:
            loan.restructured_to_id = res.id
        
        for rebate in rebate_list:
            rebate.rebate_target_consolidated_loan_id = res.id
        #20200127 add e
            
#         for r in self.line_ids:
#             #20200122 mod
# #             loan = self.env['wc.loan'].browse(r.loan_id)
#             loan = r.loan_id
#             loan.write({'restructured_to_id' : res.id,
#                         'state':'restructured'})
#             
#         #20200122 add rebate record start
#             res2 = self.env['wc.loan.payment.rebate'].create({
#                 'name': 'Rebate at consolidate',
#                 'loan_id': loan.id,
#                 'date': self.date,
#                 'amount':r.rebate_amount,
#                 'note':'This rebate is paid back in consolidated loan by decreading of its consolidated loan deduction',
#                 'is_rebate_to_member_account': False,
#                 'is_rebate_at_consolidation': True,
#                 'rebate_target_consolidated_loan_id': res.id,
#                 'deb_gl_account_id':r.deb_gl_account_id
#         })
#         #20200122 end
 
        view_id = self.env.ref('wc_loan.view_loan').id
        context = self._context.copy()

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
            'context':context,
        }
        
    #20200127 add
    @api.model
    def default_get(self, fields):
        rec = super(LoanConsolidate, self).default_get(fields)
        for line in rec['line_ids']:
            if line[2]['loan_id'] and rec['date']:
                loan = self.env['wc.loan'].browse(line[2]['loan_id'])
                a,b,rebate_amt = loan.get_rebate_amount_at_date(rec['date'])
                line[2]['rebate_amount'] = rebate_amt
        return rec
    
