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

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Posting(models.Model):
    _name = "wc.posting"
    _description = "Postings"
    _inherit = "mail.thread"
    _order = "name desc"

    def get_new_posting_date(self):
        company_id = self.env['res.company']._company_default_get('wc.posting')
        dates = self.env['wc.posting'].search([
            ('company_id','=', company_id.id),
        ], limit=1, order="name desc")
        if dates:
            dt = fields.Datetime.from_string(dates[0].name)
            return (dt + relativedelta(days=1)).strftime(DF)
        else:
            res = fields.Date.context_today(self)
        return res

    name = fields.Date("Date", readonly=True, states={'draft': [('readonly', False)]},
        default=get_new_posting_date, required=True, index=True)

    interest_computed = fields.Boolean("Interest Computed")

    #name = fields.Char("Reference", readonly=True, default="DRAFT")
    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.posting'))

    #deposit_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="set null")
    #delete later
    #move_id = fields.Many2one('account.move', string='General', readonly=True, ondelete="set null")
    #cd_move_id = fields.Many2one('account.move', string='Cash Disbursement', readonly=True, ondelete="set null")
    #cr_move_id = fields.Many2one('account.move', string='Cash Receipt', readonly=True, ondelete="set null")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('posted','Posted')
    ], 'State', default="draft", readonly=True, track_visibility='onchange')

    note = fields.Text('Notes', track_visibility='onchange')

    move_ids = fields.One2many('account.move', 'posting_id',
        string='Journal Entries', readonly=True)

    #payment_transaction_ids = fields.One2many('wc.loan', 'posting_id', string='Deposit Transactions')

    _sql_constraints = [
        ('date', 'unique (company_id, name)', _("Posting date must be unique.")),
    ]

    @api.model
    def get_first_open_date(self, company_id):
        #company_id = self.env['res.company'].sudo()._company_default_get('wc.posting')
        dates = self.env['wc.posting'].sudo().search([
            ('company_id','=', company_id),
            ('state','=','open'),
        ], limit=1, order="name asc")
        _logger.debug("Open dates: %s", dates)
        if dates:
            return dates[0].name
        else:
            raise Warning(_("There is no open date found. Please create a new posting date."))

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise Warning(_('You cannot delete a non-draft record.'))
        return super(Posting, self).unlink()

    @api.multi
    def open_date(self):

        interest_id = self.env.ref('wc_account.tr_int')
        if not interest_id:
            res = self.env['wc.tr.code'].sudo().search([
                ('code','=','INT'),
                ('trans_type','=','sa')
            ], limit=1)
            if not res:
                raise Warning(_("No INT transaction code defined."))
            interest_id = res[0]

        account_ids = False

        for rec in self:
            rec.state = 'open'
            #compute interest
            if (not account_ids) and (not rec.interest_computed):
                account_ids = self.env['wc.account'].sudo().search([
                    ('company_id','=',rec.company_id.id),
                    ('state','in',['open','dormant']),
                    ('account_type','!=','cbu'),
                ])
                account_ids.compute_deposit_interest(rec.name, interest_id, posting=rec)
                rec.interest_computed = True

            #TODO: use sql to optimize dormancy check
            #check for dormant accounts
            trcode_id = self.env['wc.tr.code'].search([
                ('code','=','A->D')
            ], limit=1)
            if not trcode_id:
                raise Warning(_("No transaction type defined for active to dormant (A->D)."))

            account_ids = self.env['wc.account'].sudo().search([
                ('company_id','=',rec.company_id.id),
                ('state','=','open'),
                ('account_type','=','sa'),
            ])
            account_ids.check_if_dormant(rec.name, trcode_id.id)

    @api.multi
    def add_details(self):
        #add extendable function
        pass

    @api.multi
    def close_date(self):
        start = time.time()
        _logger.debug("***#close_date: start")

        first = True
        for rec in self:
            rec.add_details()
            rec.state = 'closed'

            if first:
                first = False

                #delete all draft transactions
                #account transactions
                trans = self.env['wc.account.transaction'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT trans: %s", trans)
                if trans:
                    trans.unlink()

                coll_lines = self.env['wc.collection.line'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT coll lines: %s", coll_lines)
                if coll_lines:
                    coll_lines.unlink()

                collection = self.env['wc.collection'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT collection: %s", collection)
                if collection:
                    for coll in collection:
                        coll.loan_id = False
                        coll.loan_payment_id = False
                    collection.unlink()

                pay = self.env['wc.loan.payment'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT loan payment: %s", pay)
                if pay:
                    for p in pay:
                        p.collection_id = False
                    pay.unlink()

        _logger.debug("***#close_date: stop elapsed=%s", time.time() - start)

    @api.multi
    def set_draft(self):
        pass

    @api.multi
    def confirm_posting(self):
        for r in self:
            r.gen_moves()
            r.move_ids.post_nocheck()
            r.state = 'posted'

    @api.model
    def get_move_lines(self, rec, moves):
        pass
        #      jv  cd  cr  cash check
        #return [], [], [], 0.0, 0.0

    @api.model
    def get_journals(self):
        cr_journal_id = self.env['account.journal'].search([
            ('code', 'in', ['CR','cr'])
        ], limit=1)
        if not cr_journal_id:
            raise Warning(_("Cash receipt journal is not defined (code=CR)."))

        cd_journal_id = self.env['account.journal'].search([
            ('code', 'in', ['CV','cv'])
        ], limit=1)
        if not cr_journal_id:
            raise Warning(_("Cash disbursement journal is not defined (code=CV)."))

        jv_journal_id = self.env['account.journal'].search([
            ('code', 'in', ['JV','jv'])
        ], limit=1)
        if not cr_journal_id:
            raise Warning(_("General journal is not defined (code=JV)."))

        return jv_journal_id, cr_journal_id, cd_journal_id

    @api.multi
    def gen_moves(self):
        _logger.debug("**gen_moves: main")

        ctx = dict(self.env.context)
        ctx.update({
            'tracking_disable': True,
            'mail_create_nolog': True,
        })

        for rec in self:

            if not rec.company_id.posting_journal_id:
                raise Warning(_("Default posting journal is not defined in Companies/Branch/Account Settings."))

            #if rec.move_id:
            #    if rec.move_id.state == 'draft':
            #        rec.move_id.line_ids.unlink()
            #        rec.move_id.unlink()
            #    else:
            #        raise Warning(_('Journal Entry for this posting was posted manually.'))

            for mv in rec.move_ids:
                if mv.state == 'draft':
                    mv.line_ids.unlink()
                    mv.unlink()
                else:
                    raise Warning(_('Journal Entries for this posting was posted manually.'))

            #move_lines, tcash, tcheck = self.get_move_lines(rec.id)
            moves = {
                'jv': { 0: { 'lines': [] } },
                'cd': {},
                'cr': {},
                'lr': {},
            }
            self.get_move_lines(rec, moves)

            jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()
            if not cr_journal_id.default_credit_account_id:
                raise Warning(_("Cash receipt journal default credit account is not defined."))

            account_ids = {
                'tcash': rec.company_id.cash_account_id.id,
                'tcheck': rec.company_id.check_account_id.id,
                'tncash': cr_journal_id.default_credit_account_id.id
            }
            move_refs = {
                'jv': {
                    'journal_id': jv_journal_id.id,
                },
                'cr': {
                    'journal_id': cr_journal_id.id,
                },
                'cd': {
                    'journal_id': cd_journal_id.id,
                },
                'lr': {
                    'journal_id': cd_journal_id.id,
                },
            }
            date = rec.name

            for m in move_refs:

                move = moves[m]
                move_ref = move_refs[m]
                journal_id = move_ref['journal_id']

                _logger.debug("move %s: %s", m, "")

                for k in move.keys():
                    move_lines = []
                    coll = move[k]
                    coll_lines = merge_same(coll.get('lines',[]))
                    _logger.debug("%s coll %s: %s", m, k, coll.get('name'))
                    if coll_lines:
                        move_lines += coll_lines
                        for tname in account_ids:
                            account_id = account_ids[tname]
                            amount = coll.get(tname)
                            if amount:
                                debit, credit = to_dr_cr(amount)
                                vals = {
                                    'journal_id': journal_id,
                                    'date': date,
                                    'account_id': account_id,
                                    'name': '/',
                                    'debit': debit,
                                    'credit': credit,
                                    'partner_id': k or False,
                                }
                                move_lines.append([0,0, vals])

                        if move_lines:
                            ref = coll.get('name')
                            mvals = {
                                'company_id': rec.company_id.id,
                                'journal_id': journal_id,
                                'date': date,
                                'ref': 'Daily Posting%s' % (ref and (" / " + ref) or ""),
                                'daily_posting': True,
                                'posting_id': rec.id,
                                #'partner_id': k or False,
                            }
                            _logger.debug("*CREATE MOVE %s: %s", m, mvals)
                            mvals.update({
                                'line_ids': move_lines
                            })
                            _logger.debug("lines: %s", move_lines)
                            new_move = self.env['account.move'].with_context(ctx).create(mvals)

            return


#
