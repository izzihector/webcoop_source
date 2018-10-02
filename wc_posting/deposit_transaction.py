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

CHECK_CODES = set([
    'CHK0',
    'LCKD',
    'RCHK',
    'RCKD',
])

class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        required=False, readonly=True, ondelete="set null")

    date = fields.Date(default=get_first_open_date, states={})

    @api.model
    def create(self, vals):
        _logger.debug("**TRANS create: %s", vals)
        if not vals.get('trcode_id'):
            tr_int = self.env.ref('wc_account.tr_int')
            vals.update({
                'trcode_id':  tr_int and tr_int.id or False
             })
        #_logger.debug("**TRANS create2: %s", vals)
        return super(AccountTransaction, self).create(vals)

    @api.multi
    def clear_check(self):
        for r in self:
            if r.state == 'clearing':
                r.date = self.get_first_open_date()
        return super(AccountTransaction,self).clear_check()


class Posting(models.Model):
    _inherit = "wc.posting"

    deposit_account_transaction_ids = fields.One2many('wc.account.transaction',
        'posting_id', string='Deposit Transactions', readonly=True)

    @api.multi
    def add_details(self):
        #self.remove_deposit_details()
        for rec in self:
            _logger.debug("**dep add_details: %s", rec.name)

            rec.sudo().deposit_account_transaction_ids.write({
                'posting_id': False
            })
            _logger.debug("**dep add_details: removed details")

            trans_for_approval = self.env['wc.account.transaction'].sudo().search([
                ('company_id','=',rec.company_id.id),
                ('date','=',rec.name),
                ('state','=','for-approval'),
                ('posting_id','=',False),
            ])
            _logger.debug("**dep add_details: for appoval count=%s", len(trans_for_approval))

            if trans_for_approval:
                raise Warning(_("Unable to continue. There are still unapproved deposit account transactions."))

            if 1:
                #optimized with direct sql
                self.env.cr.execute("""
                    UPDATE wc_account_transaction
                        SET posting_id=%s
                    WHERE company_id = %s
                        AND date = %s
                        AND (state = 'confirmed')
                        AND (posting_id IS NULL)
                        AND ((deposit>0.0) OR (withdrawal>0.0))
                    """, (rec.id, rec.company_id.id, rec.name))
                self.env['wc.account.transaction'].invalidate_cache()
            else:
                trans = self.env['wc.account.transaction'].sudo().search([
                    ('company_id','=',rec.company_id.id),
                    ('date','=',rec.name),
                    ('state','=','confirmed'),
                    ('posting_id','=',False),
                    '|',
                        ('deposit','>',0.0),
                        ('withdrawal','>',0.0),
                ])
                _logger.debug("**dep add_details: trans count=%s", len(trans))
                trans.write({
                    'posting_id': rec.id
                })
            _logger.debug("**dep add_details: done")

            #trans = self.env['wc.account.transaction'].sudo().search([
            #    ('company_id','=',rec.company_id.id),
            #    ('date','=',rec.name),
            #    ('state','in',['confirmed','for-approval']),
            #    ('posting_id','=',False),
            #])
            #for tr in trans:
            #    _logger.debug("**dep add_details: %s d=%s w=%s", tr.name, tr.deposit, tr.withdrawal)
            #    if tr.state == 'for-approval':
            #        raise Warning(_("Unable to continue. There are still unapproved deposit account transactions."))
            #    if tr.deposit>0.0 or tr.withdrawal>0.0:
            #        tr.posting_id = rec.id
        return super(Posting, self).add_details()

    @api.multi
    def set_draft(self):
        self.remove_deposit_details()
        return super(Posting, self).set_draft()

    @api.model
    def process_noncash_code(self, dep, vals):
        self.ensure_one()

        if dep.trcode_id.code in ['CSW','200'] and dep.account_type_id.gl_withdraw_account_id:
            nvals = dict(vals)
            #nvals['debit'] = vals['credit']
            #nvals['credit'] = vals['debit']
            nvals.update({
                'name': '/',
                'debit': vals['credit'],
                'credit': vals['debit'],
                'account_id': dep.account_type_id.gl_withdraw_account_id.id,
                'partner_id': dep.teller_id.partner_id.id,
            })
            _logger.debug("*withdrawal: %s", nvals)
            return nvals

        elif dep.trcode_id.code in ['CM00','3000']:
            nvals = dict(vals)
            nvals['debit'] = vals['credit']
            nvals['credit'] = vals['debit']
            nvals.update({
                'debit': vals['credit'],
                'credit': vals['debit'],
                'account_id': dep.company_id.cash_account_id.id,
                'partner_id': dep.teller_id.partner_id.id,
            })
            return nvals

        else:
            return False

    @api.model
    def get_move_lines(self, rec, moves):
        #move_lines, tcash, tcheck = super(Posting, self).get_move_lines(posting_id)
        res = super(Posting, self).get_move_lines(rec, moves)

        #rec = self.browse(posting_id)
        #journal_id = rec.company_id.posting_journal_id.id
        jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()

        date = rec.name

        tdebit = 0.0
        tcredit = 0.0
        #tinterest = 0.0
        tinterest = {}

        for dep in rec.sudo().deposit_account_transaction_ids:
            #_logger.debug("*TRANS: %s", dep.name)
            debit, credit = to_dr_cr(dep.withdrawal - dep.deposit)
            teller_id = dep.teller_id.partner_id.id
            is_withdrawal = False

            #loan approvals and from collection are note added on general posting
            if (dep.reference!='loan approval') and (debit>0.0 or credit>0.0):
                tdebit += debit
                tcredit += credit

                if dep.trcode_id.code in ['CSW','200'] and dep.account_type_id.gl_withdraw_account_id:
                    journal = 'jv'
                    journal_id = jv_journal_id.id
                    is_withdrawal = True
                elif dep.collection_id and not dep.collection_id.in_branch:
                    journal = 'jv'
                    journal_id = jv_journal_id.id
                else:
                    if dep.trcode_id.code == 'INT':
                        #fix #243
                        journal = 'jv'
                        journal_id = jv_journal_id.id
                    elif credit>0.0 or dep.collection_id:
                        journal = 'cr'
                        journal_id = cr_journal_id.id
                    else:
                        journal = 'cd'
                        journal_id = cd_journal_id.id

                move = moves[journal]

                if dep.account_type_id.gl_interest_account_id:
                    interest_account_id = dep.account_type_id.gl_interest_account_id.id
                else:
                    interest_account_id = rec.company_id.interest_account_id.id

                #use configured glaccount defined in dep account types, else use glaccount defined in company
                account_id = False
                if dep.account_type_id.gl_account_id:
                    account_id = dep.account_type_id.gl_account_id
                elif dep.account_type=='cbu':
                    account_id = rec.company_id.cbu_deposit_account_id
                elif dep.account_type=='sa':
                    account_id = rec.company_id.sa_deposit_account_id
                elif dep.account_type=='td':
                    account_id = rec.company_id.td_deposit_account_id
                else:
                    raise Warning(_("Default deposit products GL account is not defined in Companies/Branch/Account Settings."))

                vals = {
                    #'move_id': move.id,
                    'journal_id': journal_id,
                    'date': date,
                    'account_id': account_id.id,
                    'name': "%s %s %s %s" % (
                        dep.account_id.code,
                        dep.account_type.upper(),
                        dep.trcode_id.code,
                        dep.reference or ""
                    ),
                    'partner_id': dep.account_id.member_id.partner_id.id,
                    'debit': debit,
                    'credit': credit,
                }
                _logger.debug("*add line0: %s", vals)
                #move_lines.append([0,0, vals])

                ttype = 'tcash'
                if dep.collection_id and not dep.collection_id.in_branch:
                    ttype = 'tncash'
                elif dep.trcode_id.code in CHECK_CODES:
                    ttype = 'tcheck'

                if teller_id not in move:
                    move[teller_id] = {
                        'lines': [],
                        'tcash': 0.0,
                        'tcheck': 0.0,
                        'tncash': 0.0,
                        'name': dep.teller_id.name,
                    }

                #process other tr_codes e.g. interbranch
                nvals = rec.process_noncash_code(dep, vals)
                if nvals:
                    _logger.debug("*add line1: %s", nvals)

                    vals.update({'journal_id': jv_journal_id.id})
                    nvals.update({'journal_id': jv_journal_id.id})

                    if dep.collection_id and not dep.collection_id.in_branch:
                        if not cr_journal_id.default_credit_account_id:
                            raise Warning(_("Cash receipt journal default credit account is not defined."))
                        account_id = cr_journal_id.default_credit_account_id.id
                        nvals.update({'account_id': account_id})

                    if dep.collection_id or is_withdrawal:
                        move[teller_id]['lines'].append([0, 0, vals])
                        move[teller_id]['lines'].append([0, 0, nvals])
                    else:
                        moves['jv'][0]['lines'].append([0, 0, vals])
                        moves['jv'][0]['lines'].append([0, 0, nvals])
                elif dep.trcode_id.code == 'INT':
                    #tinterest += credit - debit
                    tinterest[interest_account_id] = tinterest.get(interest_account_id, 0.0) + credit - debit
                    vals.update({'journal_id': jv_journal_id.id})
                    moves['jv'][0]['lines'].append([0, 0, vals])
                else:
                    move[teller_id]['lines'].append([0, 0, vals])
                    move[teller_id][ttype] += credit - debit

        #if tinterest != 0.0:
        for int_acct_id in tinterest:
            interest_amount = tinterest[int_acct_id]
            debit, credit = to_dr_cr(interest_amount)
            _logger.debug("*INTEREST: debit=%0.2f credit=%0.2f",
                debit,
                credit,
            )
            vals = {
                #'move_id': move.id,
                'journal_id': journal_id,
                'date': date,
                'account_id': int_acct_id, #interest_account_id.id,
                'name': 'Interest',
                'debit': debit,
                'credit': credit,
            }
            _logger.debug("*add line2: %s", vals)
            #move.line_ids.create(vals)
            #move_lines.append([0,0, vals])
            moves['jv'][0]['lines'].append([0, 0, vals])

        #return move_lines, tcash, tcheck
        return res


    @api.multi
    def gen_moves(self):
        _logger.debug("**gen_moves: deposit transactions")
        for rec in self:
            if not rec.company_id.sa_deposit_account_id:
                raise Warning(_("Default savings deposit GL account is not defined in Companies/Branch/Account Settings."))

            if not rec.company_id.td_deposit_account_id:
                raise Warning(_("Default time deposit GL account is not defined in Companies/Branch/Account Settings."))

            if not rec.company_id.cash_account_id:
                raise Warning(_("Default cash GL account is not defined in Companies/Branch/Account Settings."))

            if not rec.company_id.check_account_id:
                raise Warning(_("Default cash GL account is not defined in Companies/Branch/Account Settings."))

            if not rec.company_id.interest_account_id:
                raise Warning(_("Default interest GL account is not defined in Companies/Branch/Account Settings."))

            #rec.add_deposit_details()

        res = super(Posting, self).gen_moves()

        return res


#
