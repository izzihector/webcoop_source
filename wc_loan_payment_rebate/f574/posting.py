# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
# from util import *
from ...wc_posting import util
import time


_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Posting(models.Model):
    _inherit = "wc.posting"

    payment_rebate_ids = fields.One2many('wc.loan.payment.rebate', 
         'posting_id',readonly=True, string='Payment Rebate')




    @api.multi
    def set_draft(self):
        self.sudo().payment_rebate_ids.write({
            'posting_id': False
        })

    @api.multi
    def add_details(self):
        self.set_draft()
        for r in self:
            _logger.debug("posting rebate: search for draft.")

            recs = self.env['wc.loan.payment.rebate'].sudo().search([
                ('company_id','=',r.company_id.id),
                ('state','=','draft'),
            ])
            if recs:
                s = "\n".join(["%s" % l.name for l in recs])
                raise Warning(_("Cannot continue! There are still pending unconfirmed rebate entry.\n%s") % s)

            recs = self.env['wc.loan.payment.rebate'].sudo().search([
                ('company_id','=',r.company_id.id),
                ('state','in',['confirmed']),
            ])

            recs = self.env['wc.loan.payment.rebate'].sudo().search([
                ('company_id','=',r.company_id.id),
                ('date','=',r.name),
                ('state','=','confirmed'),
                ('posting_id','=',False),
            ])
            recs.write({
                'posting_id': r.id
            })
        return super(Posting, self).add_details()


    @api.model
    def get_move_lines(self, rec, moves):
        res2 = super(Posting, self).get_move_lines(rec, moves)
        jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()

        date = rec.name
        ctx3 = {'ir_sequence_date': date}

        dep_acct_trans_obj = self.env['wc.account.transaction'].sudo()
        trcode_cbu = dep_acct_trans_obj.get_deposit_code_cbu()
        trcode_sa = dep_acct_trans_obj.get_deposit_code_sa()
        deposit_transactions = []

        _logger.debug("*get_move_lines: debate=%s", len(rec.payment_rebate_ids))
        for rebate in rec.payment_rebate_ids:
            move_lines = []

            debit, credit = util.to_dr_cr(rebate.amount)
            partner_id =rebate.member_id.partner_id.id
            
            vals = {
                'journal_id': cd_journal_id.id,
                'date': date,
                'account_id': rebate.deb_gl_account_id.id,
                'name': "Rebate %s" % (rebate.name),
                'partner_id': partner_id,
                'debit': debit,
                'credit': credit,
            }
            move_lines.append([0, 0, vals])

            tcash = -rebate.amount
            debit, credit = util.to_dr_cr(tcash)
            vals = {
                'journal_id': cd_journal_id.id,
                'date': date,
                'account_id': rec.company_id.cash_account_id.id,
                'name': "Rebate %s " % (rebate.name),
                'partner_id': partner_id,
                'debit': debit,
                'credit': credit,
            }
            move_lines.append([0, 0, vals])

            if move_lines:
                k = partner_id or 0
                ref = "Rebate / %s " % (rebate.name)
                if k not in moves['cd']:
                    moves['cd'][k] = {
                        'lines': [],
                        'tcash': 0.0,
                        'tcheck': 0.0,
                        'tncash': 0.0,
                        'name': ref,
                    }
                moves['cd'][k]['lines'] += move_lines

        return res2


#
