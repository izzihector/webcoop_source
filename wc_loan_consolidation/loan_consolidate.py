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

class LoanConsolidateLine(models.TransientModel):
    _name = "wc.loan.consolidate.line"
    header_id = fields.Many2one('wc.loan.consolidate') 
    loan_id = fields.Integer()
    loan_name = fields.Char()
    principal_balance = fields.Float()
    interest_balance = fields.Float()
    penalty_due = fields.Float()
    date_start = fields.Date()
    date_maturity = fields.Date()

class LoanConsolidate(models.TransientModel):
    _name = "wc.loan.consolidate"
    _description = "Loan Consolidate"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan.consolidate'))

    member_id = fields.Many2one('wc.member', 'Maker', readonly=True)
    
    date = fields.Date('Date',readonly=True,
        default=fields.Date.context_today, required=True, index=True)
        
    consolidated_new_loan_type = fields.Many2one('wc.loan.type','New Loan Type',required=True)
    new_loan_amount = fields.Float('New Loan Amount',required=True)
    line_ids = fields.One2many('wc.loan.consolidate.line','header_id')

#     loan_ids = fields.One2many('wc.loan','consolidation_target_loan')

    @api.constrains('new_loan_amount')
    def check_new_loan_amount(self):
        for r in self:
            if r.new_loan_amount <=0 :
                raise UserError(_("Please set New Loan Amount"))
        
        
#get selected loan info and make form data
    @api.model
    def default_get(self, fields):
        rec = super(LoanConsolidate, self).default_get(fields)
        _logger.debug("LoanConsolidate: default_get")
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(_("Programmation error: wizard action executed without active_model or active_ids in context."))
        if active_model != 'wc.loan':
            raise UserError(_("Programmation error: the expected model for this action is 'wc.loan'. The provided one is '%d'.") % active_model)
#         if len(active_ids)<2:
#             raise UserError(_("Only 1 loan selected. Use [Restructure Loan] button on loan."))

        loans = self.env[active_model].browse(active_ids)

        self.line_ids.unlink()
        lines = []
        
        seq = 0
        for loan in loans:
            if loan.state not in ['approved','past-due']:
                raise UserError(_("You can only consolidate for approved or past due loans."))
            if loan.member_id != loans[0].member_id:
                raise UserError(_("Loans from different member is selected.Please select same member's loan."))

            seq += 10
            lines.append([0, 0, {
#                 'sequence': seq,
#                 'loan_id': loan,
                'loan_id': loan.id,
                'loan_name':loan.name,
                'principal_balance':loan.principal_balance,
                'interest_balance':loan.interest_balance,
                'penalty_due':loan.penalty_due,
                'date_start':loan.date_start,
                'date_maturity':loan.date_maturity,
            }])

        _logger.debug("LoanMultiPayment: add lines %s", lines)

        rec.update({
            'member_id': loans[0].member_id.id,
            'date': self.env['wc.posting'].get_first_open_date(self.env.user.company_id.id),
#             'editable_date': self.env.user.company_id.editable_loan_date,
            'line_ids': lines,
        })
        return rec


    @api.multi
    def move_to_consolidate_restructured(self):
        self.ensure_one()
        int_amount = 0.0
        penalty_amount = 0.0

        lines = []
        n = 0
        for r in self.line_ids:
            loan = self.env['wc.loan'].browse(r.loan_id)
            
            #check if the company allow restructure
            if not loan.is_allowed_restructure:
                raise UserError(_("Cannot restructure this loan [%s]. This loan may be already restructured. If you allow second term restructure, modify company setting.") % (loan.name))
                        
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
                    'gl_account_id': self.get_penalty_account_id(),
                }
                lines.append( (0, False, val) )
        #
        res = self.copy_and_create_restructured_loan(lines)
        for r in self.line_ids:
            loan = self.env['wc.loan'].browse(r.loan_id)
            loan.write({'restructured_to_id' : res.id,
                        'state':'restructured'})
 
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
        
    @api.multi
    def copy_and_create_restructured_loan(self,lines=[]):
        self.ensure_one()
        #modify start b561  ,f571
        loan_type = self.consolidated_new_loan_type
        res = self.env['wc.loan'].create({
#             'restructured_from_id': self.id,
            'loan_type_id': loan_type.id,
            'maturity': loan_type.maturity,
            'maturity_period': loan_type.maturity_period,
            'payment_schedule': loan_type.payment_schedule,
#             'term_payments': loan_type.term_payments,
            'term_payments_for_input':loan_type.term_payments_for_input,#add this line f571
            'schedule_making_type':loan_type.schedule_making_type,#add this line f571
            'is_fixed_payment_amount': loan_type.is_fixed_payment_amount,
            'interest_rate': loan_type.interest_rate,
            'amount': self.new_loan_amount,
            'term_payments': loan_type.term_payments_for_input,
            'company_id': self.company_id.id,
            'member_id': self.member_id.id,
#             'comaker_ids': self.comaker_ids,
            'deduction_ids': lines,
            'penalty_rate': loan_type.penalty_rate,#add this line b596
            'payment_schedule_xdays': loan_type.payment_schedule_xdays,#add this line f561
            'is_interest_deduction_first':loan_type.is_interest_deduction_first, #add 20191125 for fixing found bug on 20191125
            'days_in_year':loan_type.days_in_year, #add 20191125 for fixing found bug on 20191125
            'bulk_principal_payment': loan_type.bulk_principal_payment, #add 20191125 for fixing found bug on 20191125
        })
        return res
        #modify end b561  ,f571
        
    
