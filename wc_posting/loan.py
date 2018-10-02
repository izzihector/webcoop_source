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
import time
from util import *
EPS = 0.00001

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

def Xto_dr_cr(amt):
    if amt>=0.0:
        return amt, 0.0
    else:
        return 0.0, - amt


class LoanAdjustmentWizard(models.TransientModel):
    _inherit = "wc.loan.adjustment.wizard"

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    date = fields.Date(default=get_first_open_date, readonly=True)


class LoanAdjustment(models.Model):
    _inherit = "wc.loan.adjustment"

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    #date = fields.Date(default=get_first_open_date, readonly=True)
    date = fields.Date(default=get_first_open_date)


class Loan(models.Model):
    _inherit = "wc.loan"

    @api.model
    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    date = fields.Date(default=get_first_open_date, states={})
    #date = fields.Date(default=get_first_open_date)
    date_start = fields.Date(default=get_first_open_date)

    posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        copy=False, required=False, readonly=True, ondelete="set null")
    past_due_posting_id = fields.Many2one('wc.posting', string='Past Due Post',
        copy=False, required=False, readonly=True, ondelete="set null")
    past_due_amount = fields.Float("Past Due Amount", digits=(12,2), readonly=True)

    gl_posted = fields.Boolean("Posted", compute="_is_posted")

    editable_date = fields.Boolean("Editable Date",
        related="company_id.editable_loan_date", readonly=True)

    @api.multi
    def generate_schedule(self):
        for r in self:
            if r.state=='draft':
                ndate = self.get_first_open_date()
                if r.date!=ndate:
                    if r.editable_date and r.date:
                        if r.date>=self.env.user.company_id.start_date:
                            r.date = ndate
                            #raise ValidationError(_("Approval date should be equal to open posting date or prior to beginning date."))
                    else:
                        r.date = ndate
                _logger.debug("gen sched: date=%s", r.date)
        return super(Loan, self).generate_schedule()

    @api.model
    def get_ar_account_id(self):
        #get receivable acct, if past-due, use ar_pd
        res = False
        if self.state=='past-due':
            if self.loan_type_id.ar_pd_account_id:
                res = self.loan_type_id.ar_pd_account_id.id
            else:
                res = self.env.user.company_id.ar_pd_account_id.id
        if not res:
            res = super(Loan, self).get_ar_account_id()
        if not res:
            res = self.env.user.company_id.ar_account_id.id
        if not res:
            raise Warning(_("Loan receivable GL account is not set in Companies/Branch/Account Settings or Loan Type."))
        return res

    @api.model
    def get_ap_account_id(self):
        res = super(Loan, self).get_ap_account_id() \
            or self.env.user.company_id.ap_account_id.id
        if not res:
            raise Warning(_("Account Payable GL account is not set in Companies/Branch/Account Settings or Loan Type."))
        return res

    @api.model
    def get_interest_income_account_id(self):
        res = super(Loan, self).get_interest_income_account_id() \
            or self.env.user.company_id.interest_income_account_id.id
        if not res:
            raise Warning(_("Interest income GL account is not set in Companies/Branch/Account Settings or Loan Type."))
        return res

    @api.model
    def get_penalty_account_id(self):
        res = super(Loan, self).get_penalty_account_id() \
            or self.env.user.company_id.penalty_account_id.id
        if not res:
            raise Warning(_("Penalty GL account is not set in Companies/Branch/Account Settings or Loan Type."))
        return res

    @api.multi
    def back_to_draft(self):
        for loan in self:
            if loan.state=='cancelled':
                mdate = self.get_first_open_date()
                loan.date = '1900-01-01'
                loan.date_start = mdate
                loan.date = mdate
        return super(Loan, self).back_to_draft()

    @api.multi
    def back_to_draft2(self):
        for loan in self:
            if loan.posting_id:
                raise Warning(_("Cannot force to draft loans if date is closed."))

            loan.payments.unlink()

            if loan.details:
                for det in loan.details:
                    det.adjustments.unlink()
                    det.distributions.unlink()
                loan.details.sudo().unlink()

            #loan.amortizations.unlink()
            for a in loan.amortizations:
                a.state = 'open'
            loan.state = 'draft'

    @api.depends('posting_id')
    def _is_posted(self):
        for r in self:
            if r.posting_id:
                r.gl_posted = True

    @api.multi
    def process_past_due(self, date):

        pdate =  fields.Datetime.from_string(date)
        amort_lines = []
        start = time.time()

        for loan in self:

            if loan.state in ['approved','past-due']:
                _logger.debug("process_past_due: %s", loan.name)

                #no amortization line create if lumpsum
                if loan.payment_schedule=='lumpsum':
                    continue

                last_amort = loan.amortizations[-1]
                date_start = fields.Datetime.from_string(last_amort.date_due)
                date_due = date_start + relativedelta(months=1)
                seq = last_amort.sequence
                adate = False

                #TODO: fix #135 - add bill in advance.
                #while (pdate>=date_due):
                while (pdate>=date_start):
                    seq += 1

                    vals = self.env.cr.mogrify("(nextval('wc_loan_amortization_id_seq'),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (
                        #nextval('wc_loan_amortization_id_seq'),
                        loan.id,
                        date_start.strftime(DF),
                        date_due.strftime(DF),
                        "Past Due %d" % seq,
                        (date_due-date_start).days,
                        0,
                        0,
                        0,
                        True,
                        seq,
                        "open",
                        self._uid,
                        self._uid,
                        fields.Datetime.now(),
                        fields.Datetime.now(),
                    ))

                    #create amortization schedule lines
                    #vals = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" % (
                    #    "nextval('wc_loan_amortization_id_seq')",
                    #    loan.id,
                    #    "'%s'" % date_start.strftime(DF),
                    #    "'%s'" % date_due.strftime(DF),
                    #    "'Past Due %d'" % seq,
                    #    (date_due-date_start).days,
                    #    0,
                    #    0,
                    #    0,
                    #    True,
                    #    seq,
                    #    "'open'",
                    #    self._uid,
                    #    self._uid,
                    #    "(now() at time zone 'UTC')",
                    #    "(now() at time zone 'UTC')"
                    #)

                    _logger.debug("amortization line: vals=%s", vals)
                    amort_lines.append(vals)

                    date_start = date_due
                    date_due += relativedelta(months=1)
                    adate = date_due

                    if loan.state == 'approved':
                        loan.state == 'past-due'

        if amort_lines:

            sql = """
                INSERT INTO wc_loan_amortization (
                    id,
                    loan_id,
                    date_start,
                    date_due,
                    name,
                    days,
                    principal_balance,
                    principal_due,
                    interest_due,
                    no_others_due,
                    sequence,
                    state,
                    create_uid,
                    write_uid,
                    create_date,
                    write_date
                ) VALUES \n"""

            s = ",".join(amort_lines)
            sql = sql + s

            _logger.debug("create amortization line: start records=%s sql=%s", len(amort_lines), sql)
            self.env.cr.execute(sql)
            self.env['wc.loan.amortization'].invalidate_cache()
            _logger.debug("create amortization line: elapsed=%s", time.time() - start)


    @api.model
    def check_past_due(self, date):
        start = time.time()
        pd_loans = self.search([
            ('date_maturity','<',date),
            ('state','=','approved')
        ])
        _logger.debug("past due search: records=%s elapsed=%s", len(pd_loans), time.time() - start)
        start = time.time()

        if pd_loans.ids:
            self._cr.execute('UPDATE wc_loan '\
               'SET state=%s, past_due_amount=principal_balance '\
               'WHERE id IN %s', ('past-due', tuple(pd_loans.ids),))
            self.env['wc.loan'].invalidate_cache()
            _logger.debug("past due write: records=%s elapsed=%s", len(pd_loans), time.time() - start)


    @api.multi
    def process_date(self, date):
        start = time.time()
        _logger.debug("process_date: %s", date)

        #post payments
        payments = self.env['wc.loan.payment'].search([
            ('date','=',date),
            ('loan_id','in',self.ids),
            ('state','in',['confirmed','semi-posted'])
        ])
        _logger.debug("payment search: res=%s elapse=%s", len(payments), time.time() - start)
        for p in payments:
            _logger.debug("post_payments: %s", p.name)
            p.post_payment_per_soa_line(p)

        start = time.time()
        pd_loans = self.env['wc.loan'].search([
            ('state','in',['approved','past-due']),
            ('payment_schedule','!=','lumpsum'),
            ('last_amortization_date_due','<=',date),
        ])
        _logger.debug("past due search2: records=%s elapsed=%s", len(pd_loans), time.time() - start)
        pd_loans.process_past_due(date)

        for loan in self:
            self.gen_soa_details(loan, date)


class Posting(models.Model):
    _inherit = "wc.posting"

    loan_approved_ids = fields.One2many('wc.loan', 'posting_id',
        string='Approved Loans', readonly=True)
    past_due_ids = fields.One2many('wc.loan', 'past_due_posting_id',
        string='Past Due Loans', readonly=True)
    payable_ids = fields.One2many('account.invoice', 'posting_id',
        string='Payables', readonly=True)

    @api.multi
    def open_date(self):
        self.remove_loans_approved()
        res = super(Posting, self).open_date()
        self.env['wc.loan'].check_past_due(self.name)
        #self.env['wc.loan'].invalidate_cache()
        #self.invalidate_cache()
        return res

    @api.multi
    def remove_loans_approved(self):
        self.sudo().loan_approved_ids.write({
            'posting_id': False
        })
        self.sudo().past_due_ids.write({
            'past_due_posting_id': False
        })

    @api.multi
    def set_draft(self):
        self.remove_loans_approved()

    #close
    @api.multi
    def add_details(self):
        self.remove_loans_approved()

        for r in self:
            _logger.debug("posting loan: search for draft.")

            #no more checking of draft #225/#213
            if 0:
                #check for draft loans
                loans = self.env['wc.loan'].sudo().search([
                    ('company_id','=',r.company_id.id),
                    ('state','=','draft'),
                ])
                if loans:
                    s = "\n".join(["%s" % l.name for l in loans])
                    raise Warning(_("Cannot continue! There are still pending unapproved loans.\n%s") % s)

            #process payments and loan amortization
            loans = self.env['wc.loan'].sudo().search([
                ('company_id','=',r.company_id.id),
                ('state','in',['approved','past-due']),
            ])
            loans.process_date(r.name)

            #add to account newly approved loans
            loans = self.env['wc.loan'].sudo().search([
                ('company_id','=',r.company_id.id),
                ('date','=',r.name),
                ('state','not in',['draft','cancelled']),
                ('posting_id','=',False),
            ])
            loans.write({
                'posting_id': r.id
            })
            #for loan in loans:
            #    loan.posting_id = r.id

            #process past-due loans
            loans = self.env['wc.loan'].search([
                ('company_id','=',self.env.user.company_id.id),
                ('date','<',r.name),
                ('past_due_posting_id','=',False),
                ('state','=','past-due'),
            ])
            loans.write({
                'past_due_posting_id': r.id
            })

        return super(Posting, self).add_details()

    #no more pass to payable. direct cash/check to voucher
    @api.multi
    def Xconfirm_posting(self):
        #don't pass to payable
        self.add_payables()

        ctx = dict(self.env.context)
        ctx.update({
            'tracking_disable': True,
            'mail_create_nolog': True,
        })

        t0 = time.time()
        for p in self:
            for payable in p.payable_ids:
                _logger.debug("payable: confirm %s", payable.name)
                payable.sudo().with_context(ctx).action_invoice_open()
            _logger.debug("payable confirm: count=%s time=%s", len(p.payable_ids), time.time() - t0)

        res = super(Posting, self).confirm_posting()

        #self.env['wc.loan'].invalidate_cache()
        #self.invalidate_cache()
        return res

    @api.multi
    def add_payables(self):
        return

    #post moves
    @api.model
    def get_move_lines(self, rec, moves):
        res2 = super(Posting, self).get_move_lines(rec, moves)
        #move_lines, tcash, tcheck = super(Posting, self).get_move_lines(posting_id)

        #rec = self.browse(posting_id)
        #journal_id = rec.company_id.posting_journal_id.id
        jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()

        date = rec.name
        ctx3 = {'ir_sequence_date': date}
        dep_acct_trans_obj = self.env['wc.account.transaction'].sudo()
        trcode_cbu = dep_acct_trans_obj.get_deposit_code_cbu()
        trcode_sa = dep_acct_trans_obj.get_deposit_code_sa()
        deposit_transactions = []

        _logger.debug("*get_move_lines: approved loans=%s", len(rec.loan_approved_ids))
        for loan in rec.loan_approved_ids:
            move_lines = []
            tcheck2 = 0.0
            tcash2 = 0.0
            vals = {
                'journal_id': cd_journal_id.id,
                'date': date,
                'account_id': loan.get_ar_account_id(),
                'name': "Loan %s %s" % (loan.code, 'Receivable'),
                'partner_id': loan.member_id.partner_id.id,
                'debit': loan.amount,
                'credit': 0,
            }
            move_lines.append([0, 0, vals])

            if loan.is_check_payment:
                tcheck2 -= loan.amount
            else:
                tcash2 -= loan.amount

            #deductions
            for ded in loan.deduction_ids:
                if ded.amount != 0.0 and ded.net_include:
                    if not ded.gl_account_id.id:
                        raise Warning( _("GL Account for loan deduction ") + ded.name + _(" is not set"))

                    vals = {
                        'journal_id': cd_journal_id.id,
                        'date': date,
                        'account_id': ded.gl_account_id.id,
                        'name': "Loan %s %s" % (loan.code, ded.name),
                        'partner_id': loan.member_id.partner_id.id,
                        'debit': 0,
                        'credit': ded.amount,
                    }
                    _logger.debug("*add ded: %s", vals)
                    move_lines.append([0, 0, vals])

                    if loan.is_check_payment:
                        tcheck2 += ded.amount
                    else:
                        tcash2 += ded.amount

                    if ded.deposit_account_id:
                        if ded.deposit_account_id.account_type=='cbu':
                            trtype_id = trcode_cbu.id
                        else:
                            trtype_id = trcode_sa.id
                        val2 = {
                            'account_id': ded.deposit_account_id.id,
                            'date': rec.name,
                            'deposit': ded.amount,
                            'trcode_id': trtype_id,
                            'reference': 'loan approval',
                            'loan_id': loan.id,
                            'posting_id': rec.id,
                            'teller_id': self.env.user.id,
                            'state': 'confirmed',
                            'company_id': loan.company_id.id,
                            'name': self.env['ir.sequence'].with_context(**ctx3).next_by_code('wc.account.transaction'),
                        }
                        _logger.debug("*add dep trans: %s", val2)
                        deposit_transactions.append(val2)

            release_id = loan.released_by_id or loan.prepared_by_id
            #partner_id = release_id and release_id.partner_id.id or False
            partner_id = loan.member_id.partner_id.id
            if tcheck2:
                debit, credit = to_dr_cr(tcheck2)
                vals = {
                    'journal_id': cd_journal_id.id,
                    'date': date,
                    'account_id': rec.company_id.check_account_id.id,
                    'name': "Loan %s Release Check#%s" % (loan.code, loan.check_number or "---"),
                    #'partner_id': loan.member_id.partner_id.id,
                    'partner_id': partner_id,
                    'debit': debit,
                    'credit': credit,
                }
                move_lines.append([0, 0, vals])

            if tcash2:
                debit, credit = to_dr_cr(tcash2)
                vals = {
                    'journal_id': cd_journal_id.id,
                    'date': date,
                    'account_id': rec.company_id.cash_account_id.id,
                    'name': "Loan %s Release" % loan.code,
                    #'partner_id': loan.member_id.partner_id.id,
                    'partner_id': partner_id,
                    'debit': debit,
                    'credit': credit,
                }
                move_lines.append([0, 0, vals])

            if move_lines:
                k = partner_id or 0
                ref = "Loan Release / %s " % (loan.name)
                if k not in moves['lr']:
                    moves['lr'][k] = {
                        'lines': [],
                        'tcash': 0.0,
                        'tcheck': 0.0,
                        'tncash': 0.0,
                        'name': ref,
                    }
                moves['lr'][k]['lines'] += move_lines

        if deposit_transactions:
            #fields = deposit_transactions[0].keys()
            sql = prepare_insert_sql2(self.env.cr, self._uid, "wc_account_transaction", deposit_transactions)
            t1 = time.time()
            _logger.debug("add trans batch: count=%s sql=%s\n", len(deposit_transactions), sql)
            #self.env.cr.executemany(sql, deposit_transactions)
            self.env.cr.execute(sql, deposit_transactions)
            self.env['wc.account.transaction'].invalidate_cache()
            _logger.debug("add trans batch: time=%s", time.time() - t1)
            #recompute total
            ids = [ln['account_id'] for ln in deposit_transactions]
            accounts = self.env['wc.account'].sudo().browse(ids)
            accounts.compute_total()

        #############

        _logger.debug("*get_move_lines: loans pd=%s", len(rec.past_due_ids))

        for loan in rec.past_due_ids:
            loan_type_id = loan.loan_type_id
            if loan_type_id.ar_pd_account_id:
                ar_pd_account_id = loan_type_id.ar_pd_account_id.id
            else:
                ar_pd_account_id = self.env.user.company_id.ar_pd_account_id.id

            if loan_type_id.ar_account_id:
                ar_account_id = loan_type_id.ar_account_id.id
            else:
                ar_account_id = self.env.user.company_id.ar_account_id.id

            _logger.debug("*get_move_lines: ar=%s ar_pd=%s", ar_account_id, ar_pd_account_id)

            if not ar_account_id:
                raise Warning(_("Loan receivable account is not set for loan type.\n%s") % loan_type_id.name)

            if not ar_pd_account_id:
                raise Warning(_("Past due loan receivable account is not set for loan type.\n%s") % loan_type_id.name)

            if ar_pd_account_id != ar_account_id and loan.past_due_amount>EPS:
                vals1 = {
                    'journal_id': jv_journal_id.id,
                    'date': date,
                    'account_id': ar_account_id,
                    'name': "Loan past due %s" % (loan.code),
                    'partner_id': loan.member_id.partner_id.id,
                    'debit': 0,
                    'credit': loan.past_due_amount,
                }

                vals2 = {
                    'journal_id': jv_journal_id.id,
                    'date': date,
                    'account_id': ar_pd_account_id,
                    'name': "Loan past due %s" % (loan.code),
                    'partner_id': loan.member_id.partner_id.id,
                    'debit': loan.past_due_amount,
                    'credit': 0,
                }

                _logger.debug("*add loan pastdue1: %s", vals1)
                _logger.debug("*add loan pastdue2: %s", vals2)
                #move_lines.append([0,0, vals1])
                #move_lines.append([0,0, vals2])
                moves['jv'][0]['lines'].append([0, 0, vals1])
                moves['jv'][0]['lines'].append([0, 0, vals2])

        #return move_lines, tcash, tcheck
        return res2


#
