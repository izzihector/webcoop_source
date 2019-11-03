# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanPayments(models.Model):
    _inherit = "wc.loan.payment"

    is_manual_compute = fields.Boolean("Manual Compute",
        readonly=True, states={'draft': [('readonly', False)]})
    principal_amount = fields.Float("Principal", digits=(12,2),
        readonly=True, states={'draft': [('readonly', False)]})
    interest_amount = fields.Float("Interest", digits=(12,2),
        readonly=True, states={'draft': [('readonly', False)]})
    penalty_amount = fields.Float("Penalty", digits=(12,2),
        readonly=True, states={'draft': [('readonly', False)]})
    others_amount = fields.Float("Others", digits=(12,2),
        readonly=True, states={'draft': [('readonly', False)]})
    amount2 = fields.Float("Total Amount", digits=(12,2), compute="compute_amount2")

    @api.depends(
        'is_manual_compute',
        'principal_amount',
        'interest_amount',
        'penalty_amount',
        'amount',
    )
    def compute_amount2(self):
        for p in self:
            if p.is_manual_compute:
                p.amount2 = p.principal_amount + p.interest_amount + p.penalty_amount
            else:
                p.amount2 = p.amount

    @api.model
    def manual_post_payment(self, p):
        #self.principal_amount + self.interest_amount + self.penalty_amount
        _logger.debug("Manual Post Payment: pstate=%s lstate=%s", p.state, p.loan_id.state)

        if p.state=='draft' and p.loan_id.state in ['approved','past-due'] :

            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',p.loan_id.id),
                ('total_due','>',0.0),
                ('state','!=','del'),
            ], order='date_due')
            if not details:
                return

            #compute balances
            penalty_bal = 0.0
            interest_bal = 0.0
            others_bal = 0.0
            principal_bal = 0.0
            for det in details:
                penalty_bal += det.penalty + det.adjustment - det.penalty_paid
                interest_bal += det.interest_due - det.interest_paid
                others_bal += det.others_due - det.others_paid
                principal_bal += det.principal_due - det.principal_paid

            _logger.debug("Loan balance: pcp=%s int=%s pen=%d oth=%s",
                principal_bal,interest_bal,penalty_bal,others_bal
            )

            dist_lines = []
            #pamt = p.amount - p.posted_amount
            pamt = 0

            #penalty
            if (p.penalty_amount - penalty_bal) > EPS:
                raise Warning(_("Penalty amount is larger than balance. Balance = P%0.2f") % penalty_bal)
            lines, pamt = self.get_penalty_lines(p, details, p.penalty_amount)
            dist_lines += lines

            #interest due
            if (p.interest_amount - interest_bal) > EPS:
                raise Warning(_("Interest amount is larger than balance. Balance = P%0.2f") % interest_bal)
            lines, pamt = self.get_interest_lines(p, details, p.interest_amount)
            dist_lines += lines

            #others due
            if (p.others_amount - others_bal) > EPS:
                raise Warning(_("Others amount is larger than balance. Balance = P%0.2f") % others_bal)
            lines, pamt, dtrans_lines = self.get_other_lines(p, details, p.others_amount)
            dist_lines += lines

            #principal due
            if (p.principal_amount - principal_bal) > EPS:
                raise Warning(_("Principal amount is larger than balance. Balance = P%0.2f") % principal_bal)
            pcp_lines, pamt = self.get_principal_lines(p, details, p.principal_amount)
            dist_lines += pcp_lines

            #create trans
            self.post_create_trans(p, dist_lines, pcp_lines, dtrans_lines, 0.0)


#b586
#this is for lumpsum loan
    @api.model
    def manual_post_payment_special(self, p, loan_detail):
        #self.principal_amount + self.interest_amount + self.penalty_amount
        _logger.debug("Manual Post Payment Special: pstate=%s lstate=%s", p.state, p.loan_id.state)
 
        if p.state=='draft' and p.loan_id.state in ['approved','past-due'] :
 
#             details = self.env['wc.loan.detail'].search([
#                 ('loan_id','=',p.loan_id.id),
#                 ('total_due','>',0.0),
#                 ('state','!=','del'),
#             ], order='date_due')
            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',p.loan_id.id),
#                 ('total_due','>',0.0),
                ('state','!=','del'),
            ], order='date_due')

            
            if not details:
                return
 
            #compute balances
            penalty_bal = 0.0
            interest_bal = 0.0
            others_bal = 0.0
            principal_bal = 0.0
            for det in details:
                penalty_bal += det.penalty + det.adjustment - det.penalty_paid
                interest_bal += det.interest_due - det.interest_paid
                others_bal += det.others_due - det.others_paid
                principal_bal += det.principal_due - det.principal_paid
 
            _logger.debug("Loan balance: pcp=%s int=%s pen=%d oth=%s",
                principal_bal,interest_bal,penalty_bal,others_bal
            )
 
            dist_lines = []
            #pamt = p.amount - p.posted_amount
            pamt = 0
 
            #penalty
            if (p.penalty_amount - penalty_bal) > EPS:
                raise Warning(_("Penalty amount is larger than balance. Balance = P%0.2f") % penalty_bal)
            lines, pamt = self.get_penalty_lines(p, details, p.penalty_amount)
            dist_lines += lines
 
            #interest due
            if (p.interest_amount - interest_bal) > EPS:
                raise Warning(_("Interest amount is larger than balance. Balance = P%0.2f") % interest_bal)
            lines, pamt = self.get_interest_lines(p, details, p.interest_amount)
            dist_lines += lines
 
            #others due
            if (p.others_amount - others_bal) > EPS:
                raise Warning(_("Others amount is larger than balance. Balance = P%0.2f") % others_bal)
#             lines, pamt, dtrans_lines = self.get_other_lines(p, details, p.others_amount)
            lines, pamt, dtrans_lines = self.get_other_lines_for_lumpsum(p, details, p.others_amount , loan_detail)
            dist_lines += lines
 
            #principal due
            if (p.principal_amount - principal_bal) > EPS:
                raise Warning(_("Principal amount is larger than balance. Balance = P%0.2f") % principal_bal)
            pcp_lines, pamt = self.get_principal_lines(p, details, p.principal_amount)
            dist_lines += pcp_lines
 
            #create trans
            self.post_create_trans(p, dist_lines, pcp_lines, dtrans_lines, 0.0)


    @api.multi
    def confirm_payment(self):
        self.ensure_one()
        if self.is_manual_compute and self.payment_schedule=='lumpsum':
            #b586 mod
#             self.amount = self.principal_amount + self.interest_amount + self.penalty_amount
            self.amount = self.principal_amount + self.interest_amount + self.penalty_amount + self.others_amount
            return super(LoanPayments, self).confirm_payment()
        elif self.is_manual_compute and self.payment_schedule!='lumpsum':
            self.manual_post_payment(self)
        else:
            self.principal_amount = 0.0
            self.interest_amount = 0.0
            self.penalty_amount = 0.0 
            #b586 add
            self.others_amount = 0.0              
            return super(LoanPayments, self).confirm_payment()

    @api.onchange(
        'is_manual_compute',
        'principal_amount',
        'interest_amount',
        'penalty_amount',
        'others_amount',
    )
    def oc_manual_amount(self):
        self.ensure_one()
        if self.is_manual_compute:
            self.amount2 = self.principal_amount + self.interest_amount + self.penalty_amount + self.others_amount

#b586 
#     @api.model
#     def get_detail_line(self, loan, date_start):
    @api.model
    def get_detail_line(self, loan, date_start, detdel_id):
        if self.is_manual_compute:
            #b586 (same value , just for uniformity between source)
#             principal_balance = loan.principal_balance
#             principal_due = self.principal_amount
#             interest_due = self.interest_amount
#             penalty = self.penalty_amount
#             amount = principal_due + interest_due + penalty
#             self.amount = amount
            principal_balance = detdel_id.principal_balance
            original_due_date = detdel_id.date_due
            
            input_principal = self.principal_amount
            input_interest = self.interest_amount
            input_penalty = self.penalty_amount
            input_others = self.others_amount
            self.amount = input_principal + input_interest + input_penalty + input_others
            #b586 end

            #b586 mod start
#             nbalance = (principal_balance + interest_due + penalty)

            #get reconcile amount accordance with priority
            principal_current_bal,\
            interest_current_bal,\
            penalty_current_bal,\
            others_current_bal,\
            total_current_bal \
                = self.get_current_balance(detdel_id)
            
            new_interest_due=0.0
            remain_principal = 0.0
            penalty_recon = 0.0
            interest_recon = 0.0
            others_recon = 0.0
            principal_recon = 0.0
            target_bal = 0.0
            total_due = 0.0
            temp = 0.0 #temporary variable for getting return value from def
            
            #check if each amount is over due , and get amount for generate payment data
            penalty_recon,temp = self.get_partial_recon_with_check('penalty',penalty_current_bal,input_penalty)
            interest_recon,temp = self.get_partial_recon_with_check('interest',interest_current_bal,input_interest)
            others_recon,temp  = self.get_partial_recon_with_check('other',others_current_bal,input_others)
            principal_recon,temp  = self.get_partial_recon_with_check('principal',principal_current_bal,input_principal)

            total_due = total_current_bal -(penalty_recon+interest_recon+others_recon+principal_recon)
            total_due_without_int = total_current_bal - interest_current_bal \
                  -(penalty_recon + others_recon + principal_recon)
            remain_principal = principal_balance - principal_recon


#             vals = {
#                 'loan_id': loan.id,
#                 #'name': "Advance Payment %d" % n,
#                 'date_start': date_start,
#                 'date_due': self.date,
#                 'principal_balance': principal_balance,
#                 'principal_due': principal_due,
#                 'interest_due': interest_due,
#                 'penalty': penalty,
#                 'penalty_base': 0.0,
#                 'no_others_due': True,
#                 'state': 'due',
#                 'advance_payment_id': self.id,
#                 #'date_soa': fields.Date.context_today(self),
#                 #'sequence': n,
#             }
#             return vals, principal_balance, principal_due
            
            vals1 = {
                'loan_id': loan.id,
                'date_start': date_start,
                'date_due': self.date,
                'principal_balance': principal_balance,
                'principal_due': principal_recon,
                'interest_due': interest_recon,
                'state': 'due',
#                 'no_others_due': detdel_id.no_others_due,
                'advance_payment_id': self.id,
            }

            new_date_start = self.date
            new_date_due = original_due_date        
            if new_date_start > loan.date_maturity:
                if loan.state=='approved':
                    loan.state = 'past-due'
                d = fields.Date.from_string(self.date) + relativedelta(days=30)
                new_date_due =  d.strftime(DF)

            #Todo : consider penalty special rate 
            if self.loan_id.is_interest_epr:
                new_interest_due = input_interest - interest_recon
            else:
                new_interest_due = self.loan_id.compute_interest(\
                        remain_principal, new_date_start, new_date_due)

            vals2 = {
                'loan_id': loan.id,
                'date_start': new_date_start,
                'date_due': new_date_due,
                'principal_balance': remain_principal,
                'principal_due': remain_principal,
                'interest_due': new_interest_due,
                'penalty': 0.0,
                'penalty_base': 0.0,
#                 'no_others_due': True,
                'state': 'next_due',
            }
            
            vals3 = {
                'principal_recon':principal_recon,
                'interest_recon':interest_recon,
                'others_recon':others_recon,
                'penalty_recon':penalty_recon,
                'total_due':total_due,
                'total_due_without_int':total_due_without_int,                
            }

            return vals1,vals2,vals3

         
        else:
            #b586 mod
#             return super(LoanPayments, self).get_detail_line(loan, date_start)
            return super(LoanPayments, self).get_detail_line(loan, date_start ,detdel_id)





#
