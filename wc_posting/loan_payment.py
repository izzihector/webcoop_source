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
from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class LoanPayments(models.Model):
    _inherit = "wc.loan.payment"

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    date = fields.Date(default=get_first_open_date, states={}, readonly=False)
    #date = fields.Date(default=get_first_open_date)
    cancellable = fields.Boolean(compute='_compute_cancellable', store=True)

    editable_date = fields.Boolean("Editable Date",
        related="loan_id.company_id.editable_loan_date", readonly=True)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                for dist in rec.distributions:
                    if dist.posting_id:
                        raise Warning(_('You cannot delete a posted non-draft payment transaction. %s') % rec.name)
        return super(LoanPayments, self).unlink()

    @api.multi
    @api.depends('distributions','distributions.posting_id')
    def _compute_cancellable(self):
        for p in self:
            c = True
            for dist in p.distributions:
                if dist.posting_id:
                    c = False
                    break
            p.cancellable = c

    @api.multi
    def reverse_payment(self):
        trcode_cbu = self.env.ref('wc_account.tr_adjustment')
        if not trcode_cbu:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','cbu'),
                ('name','ilike','Adjustment'),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No CBU adjustment transaction type present."))
            trcode_cbu = res[0]

        trcode_sa = self.env.ref('wc_account.tr_cm00')
        if not trcode_sa:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','sa'),
                ('name','ilike','Memo'),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No account adjustment transaction type present."))
            trcode_sa = res[0]

        for p in self:
            #check there is other payments after this
            res = self.search([
                ('loan_id','=',p.loan_id.id),
                ('date','>',p.date),
                ('state','=','confirmed'),
                ('is_reversed','=',False),
            ])
            if res:
                raise Warning(_("You can only reverse last payment."))

            p.is_reversed = True

            #change details for advance payments
            for det in p.advance_detail_ids:
                #det = self.env['wc.loan.detail'].search([
                #    ('advance_payment_id','=',p.id),
                #    ('loan_id','=',p.loan_id.id),
                #])
                principal_paid = 0.0
                date1 = p.loan_id.date_start
                for d in det:
                    principal_paid += d.principal_paid
                    date1 = d.date_start
                    d.principal_balance = 0.0
                    d.principal_due = 0.0
                    d.interest_due = 0.0
                    d.penalty = 0.0
                    d.no_others_due = True
                    d.state = 'reversed'

                if principal_paid>0.0:
                    ldet = self.env['wc.loan.detail'].search([
                        ('loan_id','=',p.loan_id.id),
                        ('date_due','=',p.loan_id.date_maturity),
                    ], order='date_due desc', limit=1)

                    #FIX: #240
                    if not ldet:
                        ldet = self.env['wc.loan.detail'].search([
                            ('loan_id','=',p.loan_id.id),
                            ('date_due','>',p.loan_id.date_maturity),
                            ('principal_due','=',0.0),
                        ], order='date_due desc', limit=1)

                    for d in ldet:
                        d.principal_balance = d.principal_balance + principal_paid
                        d.principal_due = d.principal_due + principal_paid
                        d.date_start = date1
                        d.interest_due = p.loan_id.compute_interest(
                            d.principal_balance,
                            date1,
                            d.date_due
                        )
                        #fix of #240
                        d.state = 'next_due'

            #fix bug #126 - change loan status to approved if paid and was reversed
            if p.loan_id.state=='paid' and p.amount>0.0:
                p.loan_id.state = 'approved'

            p2 = self.create({
                'company_id': p.company_id.id,
                'loan_id': p.loan_id.id,
                'or_number': p.or_number,
                'check_number': p.check_number,
                'amount': -p.amount,
                'name': 'Reverse Payment %s' % p.name,
                'is_reversed': True,
                'state': 'confirmed',
                'collection_id': p.collection_id.id,
            })
            for dist in p.distributions:
                deposit_account_id = dist.deposit_account_id
                if deposit_account_id:
                    if deposit_account_id.account_type=='cbu':
                        trtype_id = trcode_cbu.id
                    else:
                        trtype_id = trcode_sa.id
                    res = self.env['wc.account.transaction'].sudo().create({
                        'account_id': deposit_account_id.id,
                        'withdrawal': dist.amount,
                        'date': p2.date,
                        'trcode_id': trtype_id,
                        'reference': 'reverse payment',
                        'loan_id': p.loan_id.id,
                        'teller_id': self.env.user.id,
                    })
                    res.confirm()
                    res.approve()

                p2.distributions.create({
                    'payment_id': p2.id,
                    'detail_id': dist.detail_id.id,
                    'payment_type': dist.payment_type,
                    'code': dist.code,
                    'amount': -dist.amount,
                    'deposit_account_id' : deposit_account_id.id,
                    'gl_account_id': dist.gl_account_id.id,
                })


class LoanPaymentDistribution(models.Model):
    _inherit = "wc.loan.payment.distribution"

    loan_id = fields.Many2one(related="payment_id.loan_id")
    or_number = fields.Char(related="payment_id.or_number")
    check_number = fields.Char(related="payment_id.check_number")
    date = fields.Date(related="payment_id.date", store=True)
    state = fields.Selection(related="payment_id.state", store=True)
    company_id = fields.Many2one(related="payment_id.company_id", store=True)

    posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        required=False, readonly=True, ondelete="set null")



class Posting(models.Model):
    _inherit = "wc.posting"

    payment_ids = fields.One2many('wc.loan.payment.distribution', 'posting_id',
        string='Loan Payments', readonly=True)

    @api.multi
    def set_draft(self):
        for rec in self:
            for pay in rec.sudo().payment_ids:
                pay.posting_id = False
        return super(Posting, self).set_draft()

    @api.multi
    def add_details(self):
        for rec in self:
            for pay in rec.sudo().payment_ids:
                pay.posting_id = False
            #payments
            payments = self.env['wc.loan.payment.distribution'].sudo().search([
                ('company_id','=',rec.company_id.id),
                ('date','=',rec.name),
                ('state','=','confirmed'),
                ('posting_id','=',False),
            ])
            for pay in payments:
                if pay.amount != 0.0 and not pay.deposit_account_id:
                    pay.posting_id = rec.id

        return super(Posting, self).add_details()

    @api.multi
    def gen_moves(self):
        _logger.debug("**gen_moves: loan payment")
        #self.env['wc.loan'].check_gl_accounts_setup()
        return super(Posting, self).gen_moves()


    @api.model
    def get_move_lines(self, rec, moves):
        res = super(Posting, self).get_move_lines(rec, moves)
        jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()
        date = rec.name

        for pay in rec.payment_ids:
            debit, credit = to_dr_cr(-pay.amount)
            collector_id = pay.create_uid.partner_id.id

            account_id = False
            if pay.gl_account_id:
                account_id = pay.gl_account_id.id
            else:
                if pay.payment_type=='penalty':
                    account_id = pay.loan_id.get_penalty_account_id()
                elif pay.payment_type=='interest':
                    account_id = pay.loan_id.get_interest_income_account_id()
                elif pay.payment_type=='principal':
                    account_id = pay.loan_id.get_ar_account_id()

            if not account_id:
                raise Warning(_("GL Account not properly set for loan deductions or payments."))

            if pay.check_number:
                #tcheck += pay.amount
                checkno = " Check#%s" % pay.check_number
            else:
                #tcash += pay.amount
                checkno= ""

            #or_number = ocp.collection_id.name and (" OR#%s" % ocp.collection_id.name) or ""
            vals = {
                #'journal_id': cr_journal_id.id,
                'date': date,
                'account_id': account_id,
                'name': "Loan payment %s %s %s%s" % (pay.loan_id.code, pay.payment_type, pay.code, checkno),
                'partner_id': pay.loan_id.member_id.partner_id.id,
                'debit': debit,
                'credit': credit,
            }
            _logger.debug("*add loan payment: %s", vals)

            if pay.payment_id.collection_id and not pay.payment_id.collection_id.in_branch:
                move = moves['jv']
                vals['journal_id'] = jv_journal_id.id
                ttype = 'tncash'
            else:
                move = moves['cr']
                vals['journal_id'] = cr_journal_id.id
                ttype = 'tcash'

            if collector_id not in move:
                move[collector_id] = {
                    'lines': [],
                    'tcash': 0.0,
                    'tcheck': 0.0,
                    'tncash': 0.0,
                    'name': pay.create_uid.name,
                }
            move[collector_id]['lines'].append([0, 0, vals])
            move[collector_id][ttype] += credit - debit

        #return move_lines, tcash, tcheck
        return res








#
