# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanMultiPayment(models.TransientModel):
    _name = "wc.loan.multipay"
    _description = "Loan Multiple Payment"

    member_id = fields.Many2one('wc.member', 'Maker', readonly=True)
    date = fields.Date('Date')
    or_number = fields.Char("O.R. Number",
        readonly=True, states={'draft': [('readonly', False)]})
    check_number = fields.Char("Check No.",
        readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Float(string='Total Amount', digits=(12,2), required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    line_ids = fields.One2many('wc.loan.multipay.line',
        'payment_id','Loans Payment Lines',
        readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft','Draft'),
        ('confirmed','Confirmed'),
    ], string='State', default='draft')
    editable_date = fields.Boolean("Editable Date")
    recompute_payment = fields.Boolean("Recompute")

    @api.model
    def default_get(self, fields):
        rec = super(LoanMultiPayment, self).default_get(fields)

        _logger.debug("LoanMultiPayment: default_get")

        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(_("Programmation error: wizard action executed without active_model or active_ids in context."))
        if active_model != 'wc.loan':
            raise UserError(_("Programmation error: the expected model for this action is 'wc.loan'. The provided one is '%d'.") % active_model)
        if len(active_ids)<2:
            raise UserError(_("Only 1 loan selected. Use [Add Payment] button on loans to register a single payment."))

        loans = self.env[active_model].browse(active_ids)

        lines = []
        seq = 0
        for loan in loans.sorted(key=lambda r: "%s-%012d" % (r.date_start, r.loan_type_id.priority)):
            if loan.state not in ['approved','past-due']:
                raise UserError(_("You can only register payments for approved or past due loans."))
            if loan.member_id != loans[0].member_id:
                raise UserError(_("You can only register payments for the same member."))
            seq += 10
            lines.append([0, 0, {
                'sequence': seq,
                'loan_id': loan.id,
                'loan_name': loan.name,
                'date_start': loan.date_start,
                'date_maturity': loan.date_maturity,
                'priority': loan.loan_type_id.priority
            }])

        _logger.debug("LoanMultiPayment: add lines %s", lines)

        rec.update({
            'member_id': loans[0].member_id.id,
            'date': self.env['wc.posting'].get_first_open_date(self.env.user.company_id.id),
            'editable_date': self.env.user.company_id.editable_loan_date,
            'line_ids': lines,
        })
        return rec

    @api.multi
    def recompute_amount(self):
        for r in self:
            r.oc_amount()
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wc.loan.multipay',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.onchange('recompute_payment')
    def oc_recompute_payment(self):
        self.ensure_one()
        if self.recompute_payment:
            self.oc_amount()
            self.recompute_payment = False

    @api.onchange('amount')
    def oc_amount(self):
        self.ensure_one()
        tamount = self.amount

        lines = self.line_ids.sorted(key=lambda r: r.sequence)

        for line in lines:
            principal_due, interest_due, penalty_due, others_due = line.compute_due(self.date)
            line.principal_due = principal_due
            line.interest_due = interest_due
            line.penalty_due = penalty_due
            line.others_due = others_due

            line.principal = 0.0
            line.interest = 0.0
            line.penalty = 0.0
            line.others = 0.0

            _logger.debug("oc_amount %s: pcp=%s int=%s pen=%s oth=%s",
                line.loan_name, principal_due, interest_due, penalty_due, others_due)

            #penalty
            penalty = min(round(penalty_due,2), tamount)
            if tamount<EPS or penalty<EPS:
                continue
            line.penalty = penalty
            tamount -= penalty
            _logger.debug("oc_amount: penalty=%s", penalty)

        #interest
        for line in lines:
            interest = min(round(line.interest_due,2), tamount)
            if tamount<EPS or interest<EPS:
                break
            line.interest = interest
            tamount -= interest
            _logger.debug("oc_amount: interest=%s", interest)

        #others
        for line in lines:
            others = min(round(line.others_due,2), tamount)
            if tamount<EPS or others<EPS:
                break
            line.others = others
            tamount -= others
            _logger.debug("oc_amount: others=%s", others)

        #principal
        for line in lines:
            principal = min(round(line.principal_due,2), tamount)
            if tamount<EPS or principal<EPS:
                break
            line.principal = principal
            tamount -= principal
            _logger.debug("oc_amount: principal=%s", principal)

        #advance principal
        for line in lines:
            if tamount<EPS:
                break
            loan = line.get_loan(line.loan_id)
            ap = min(loan.principal_balance-line.principal, tamount)
            if ap<EPS:
                raise UserError(_("Inconsistency error! Loan balance is less than due.\nPcpBal=%s Amt=%s") \
                    % (loan.principal_balance, line.principal))
            line.principal += ap
            tamount -= ap
            _logger.debug("oc_amount: adv_pcp=%s", ap)

        if tamount>EPS:
            raise UserError(_("Payment amount is greater than loan payable."))

        for line in lines:
            line.amount = line.principal +  line.interest +  line.penalty +  line.others

    @api.multi
    def confirm_payment(self):
        self.ensure_one()
        amount = sum(line.amount for line in self.line_ids)
        _logger.debug("confirm_payment: amount=%s", amount)
        if abs(amount-self.amount)>EPS:
            raise UserError(_("Total amount is not equal to total of line amounts."))

        lines = self.line_ids.sorted(key=lambda r: r.sequence)

        Payment = self.env['wc.loan.payment']
        codes = " / ".join([ line.get_loan(line.loan_id).code for line in lines ])
        note = "Part of batch payment amounting to {:,.2f}.\n%s".format(self.amount) % codes
        i = 0
        for line in lines:
            if line.amount>0.0:
                i += 1
                val = {
                    'name': 'Batch Payment %s #%d' % (self.date, i),
                    'loan_id': line.loan_id,
                    'or_number': self.or_number,
                    'check_number': self.check_number,
                    'date': self.date,
                    'amount': line.amount,
                    'note': note,
                }
                _logger.debug("confirm_payment: line=%s", val)
                Payment.create(val)


class LoanMultiPaymentLine(models.TransientModel):
    _name = "wc.loan.multipay.line"
    _description = "Loan Multiple Payment Line"
    #_order = "sequence"

    payment_id = fields.Many2one('wc.loan', 'Payment', ondelete='cascade')
    sequence = fields.Integer("Sequence")
    priority = fields.Integer("Priority", readonly=True)
    #loan_id = fields.Many2one('wc.loan', 'Loan', readonly=True, ondelete='set null')
    loan_id = fields.Integer()
    loan_name = fields.Char("Loan", readonly=True)
    date_start = fields.Date('Amort. Start', readonly=True)
    date_maturity = fields.Date('Date Maturity', readonly=True)
    amount = fields.Float(string='Amount', digits=(12,2))

    principal_due = fields.Float(string='Principal Due', digits=(12,2), readonly=True)
    interest_due = fields.Float(string='Interest Due', digits=(12,2), readonly=True)
    penalty_due = fields.Float(string='Penalty Due', digits=(12,2), readonly=True)
    others_due = fields.Float(string='Others Due', digits=(12,2), readonly=True)

    principal = fields.Float(string='Principal', digits=(12,2), readonly=True)
    interest = fields.Float(string='Interest', digits=(12,2), readonly=True)
    penalty = fields.Float(string='Penalty', digits=(12,2), readonly=True)
    others = fields.Float(string='Others', digits=(12,2), readonly=True)

    @api.model
    def get_loan(self, loan_id):
        res =  self.env['wc.loan'].browse(loan_id)
        _logger.debug("get_loan: id=%s %s", self.loan_id, res.name)
        return res

    @api.model
    def compute_due(self, date):
        self.ensure_one()
        loan = self.get_loan(self.loan_id)
        penalty_due = loan.penalty_due
        others_due = loan.others_due
        if loan.payment_schedule=='lumpsum':
            interest_due = loan.compute_interest(loan.principal_balance, loan.date_start, date)
            principal_due = loan.principal_balance
        else:
            interest_due = loan.interest_due
            principal_due = loan.principal_due
        return principal_due, interest_due, penalty_due, others_due

    @api.onchange('amount')
    def oc_amount(self):
        self.ensure_one()
        loan = self.get_loan(self.loan_id)
        tamount = self.amount
        principal_due, interest_due, penalty_due, others_due = self.compute_due(self.payment_id.date)
        _logger.debug("**line oc_amount: pcp=%s int=%s pen=%s oth=%s loan=%s",
            principal_due, interest_due, penalty_due, others_due, self.loan_name)
        penalty = 0.0
        interest = 0.0
        others = 0.0
        principal = 0.0

        if tamount > EPS:
            penalty = max(min(round(penalty_due,2), tamount), 0.0)
            tamount -= penalty

        if tamount > EPS:
            interest = max(min(round(interest_due,2), tamount), 0.0)
            tamount -= interest

        if tamount > EPS:
            others = max(min(round(others_due,2), tamount), 0.0)
            tamount -= others

        if tamount > EPS:
            if tamount > loan.principal_balance:
                raise UserError(_("Amount is more than loan payable."))
            principal = tamount

        self.principal = tamount
        self.interest = interest
        self.penalty = penalty
        self.others = others

#
