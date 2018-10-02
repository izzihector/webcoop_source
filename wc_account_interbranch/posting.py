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

def to_dr_cr(amt):
    if amt>=0.0:
        return round(amt,2), 0.00
    else:
        return 0.00, - round(amt,2)

class Posting(models.Model):
    _inherit = "wc.posting"

    interbranch_account_transaction_ids = fields.One2many('wc.account.ibtrans',
        'posting_id', string='Interbranch Deposit Transactions', readonly=True)

    @api.multi
    def add_details(self):
        _logger.debug("**ib add_details")
        for rec in self:
            for tr in rec.sudo().interbranch_account_transaction_ids:
                tr.posting_id = False

        for rec in self:

            trans_for_approval = self.env['wc.account.ibtrans'].sudo().search([
                ('company_id','=',rec.company_id.id),
                ('date','=',rec.name),
                ('state','=','for-approval'),
                ('posting_id','=',False),
            ])
            if trans_for_approval:
                raise Warning(_("Unable to continue. There are still unapproved interbranch deposit account transactions."))

            trans = self.env['wc.account.ibtrans'].sudo().search([
                ('company_id','=',rec.company_id.id),
                ('date','=',rec.name),
                ('state','=','confirmed'),
                ('posting_id','=',False),
                '|',
                    ('deposit','>',0.0),
                    ('withdrawal','>',0.0),
            ])
            trans.write({
                'posting_id': rec.id
            })
            #for tr in trans:
            #    if tr.state == 'for-approval':
            #        raise Warning(_("Unable to continue. There are still unapproved interbranch deposit account transactions."))
            #    if tr.deposit>0.0 or tr.withdrawal>0.0:
            #        tr.posting_id = rec.id
        return super(Posting, self).add_details()

    @api.model
    def process_noncash_code(self, dep, vals):
        self.ensure_one()

        if dep.trcode_id.code=='ICSD':
            amt = vals['credit'] - vals['debit']
            if amt<0.0:
                raise ValidationError(_("Interbranch deposit with negative amount."))

            if not dep.company_id.ib_receivable_account_id:
                raise Warning(_("Interbranch receivable GL account is not set."))

            nvals = dict(vals)
            nvals.update({
                'debit': amt,
                'credit': 0.0,
                'account_id': dep.company_id.ib_receivable_account_id.id,
                'partner_id': dep.other_company_id.partner_id.id,
            })
            return nvals

        elif dep.trcode_id.code=='ICSW':
            amt = vals['debit'] - vals['credit']
            if amt<0.0:
                raise ValidationError(_("Interbranch withdrawal with negative amount."))

            if not dep.company_id.ib_payable_account_id:
                raise Warning(_("Interbranch payable GL account is not set."))

            nvals = dict(vals)
            nvals.update({
                'debit': 0.0,
                'credit': amt,
                'account_id': dep.company_id.ib_payable_account_id.id,
                'partner_id': dep.other_company_id.partner_id.id,
            })
            return nvals

        else:
            return super(Posting, self).process_noncash_code(dep, vals)


    @api.model
    def get_move_lines(self, rec, moves):
        #move_lines, tcash, tcheck = super(Posting, self).get_move_lines(posting_id)
        res = super(Posting, self).get_move_lines(rec, moves)

        #rec = self.browse(posting_id)
        #journal_id = rec.company_id.posting_journal_id.id
        jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()
        date = rec.name

        receivable_glacct = rec.company_id.ib_receivable_account_id
        if not receivable_glacct:
            raise Warning(_("Interbranch receivable GL account is not set."))

        payable_glacct = rec.company_id.ib_payable_account_id
        if not payable_glacct:
            raise Warning(_("Interbranch payable GL account is not set."))

        cash_glacct = rec.company_id.cash_account_id
        if not cash_glacct:
            raise Warning(_("Cash GL account is not set."))

        tdebit = 0.0
        tcredit = 0.0

        for dep in rec.sudo().interbranch_account_transaction_ids:
            #_logger.debug("*TRANS: %s", dep.name)
            debit, credit = to_dr_cr(dep.deposit - dep.withdrawal)

            if (debit>0.0 or credit>0.0):
                tdebit += debit
                tcredit += credit

                vals = {
                    'journal_id': jv_journal_id.id,
                    'date': date,
                    'account_id': cash_glacct.id,
                    'name': "%s %s %s %s" % (
                        dep.account_id.code,
                        dep.account_type2.upper(),
                        dep.trcode_id.code,
                        dep.reference or ""
                    ),
                    'partner_id': dep.account_id.member_id.partner_id.id,
                    'debit': debit,
                    'credit': credit,
                }
                _logger.debug("*add line: %s", vals)
                moves['jv'][0]['lines'].append([0, 0, vals])

                #contra account
                if dep.trcode_id.code=='ICSD':
                    gl_account = payable_glacct
                elif dep.trcode_id.code=='ICSW':
                    gl_account = receivable_glacct
                else:
                    raise Warning(_("Interbranch transaction code is not valid.\nCode=%s") % dep.trcode_id.code)

                vals = {
                    'journal_id': jv_journal_id.id,
                    'date': date,
                    'account_id': gl_account.id,
                    'name': "%s %s %s %s" % (
                        dep.account_id.code,
                        dep.account_type2.upper(),
                        dep.trcode_id.code,
                        dep.reference or ""
                    ),
                    'partner_id': dep.other_company_id.partner_id.id,
                    'debit': credit,
                    'credit': debit,
                }
                _logger.debug("*add line: %s", vals)
                #move_lines.append([0, 0, vals])
                moves['jv'][0]['lines'].append([0, 0, vals])

        #return move_lines, tcash, tcheck
        return res
