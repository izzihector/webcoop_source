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

class InsuranceType(models.Model):
    _inherit = "wc.insurance.type"

    gl_account_id = fields.Many2one('account.account', string='GL Account', ondelete="restrict")


class Posting(models.Model):
    _inherit = "wc.posting"

    insurance_payment_ids = fields.One2many('wc.collection.line', 'posting_id',
         readonly=True, string='Insurance Payments')

    @api.multi
    def set_draft(self):
        for p in self:
            for pay in p.sudo().insurance_payment_ids:
                pay.posting_id = False
        return super(Posting, self).set_draft()

    @api.multi
    def add_details(self):
        for p in self:
            for pay in p.sudo().insurance_payment_ids:
                pay.posting_id = False
            payment_ids = self.env['wc.collection.line'].sudo().search([
                ('company_id','=',p.company_id.id),
                ('date','=',p.name),
                ('state','=','confirmed'),
                ('insurance_id','!=',False),
                ('collection_type','=','insurance'),
                ('amount','!=',0.0),
            ])
            _logger.debug("ins add_details: res=%s", payment_ids)
            for pay in payment_ids:
                pay.posting_id = p.id

        return super(Posting, self).add_details()

    @api.model
    def get_move_lines(self, rec, moves):
        res = super(Posting, self).get_move_lines(rec, moves)
        jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()
        date = rec.name

        for ins in rec.insurance_payment_ids:

            if ins.collection_id and not ins.collection_id.in_branch:
                journal = 'jv'
                journal_id = jv_journal_id.id
                ttype = 'tncash'
                rev_account_id = cr_journal_id.default_credit_account_id.id
            else:
                journal = 'cr'
                journal_id = cr_journal_id.id
                ttype = 'tcash'
                rev_account_id = rec.company_id.cash_account_id.id,

            collector_id = ins.collection_id.create_uid.partner_id.id
            if collector_id not in moves[journal]:
                moves[journal][collector_id] = {
                    'lines': [],
                    'tcash': 0.0,
                    'tcheck': 0.0,
                    'tncash': 0.0,
                    'name': ins.collection_id.create_uid.name,
                }

            debit, credit = to_dr_cr(-ins.amount)
            #tcash += ins.amount

            account_id = ins.insurance_id.type_id.gl_account_id.id
            if not account_id:
                raise Warning( _("Error!\nGL Account for microinsurance type %s is not set.") % ins.name)

            or_number = ins.collection_id.name and (" OR#%s" % ins.collection_id.name) or ""
            vals = {
                'journal_id': journal_id,
                'date': date,
                'account_id': account_id,
                'name': "%s%s" % (ins.name, or_number),
                'partner_id': ins.member_id.partner_id.id,
                'debit': debit,
                'credit': credit,
            }
            _logger.debug("*add ins move: %s", vals)

            moves[journal][collector_id]['lines'].append([0, 0, vals])

            if ins.is_reversed:
                nvals = dict(vals)
                nvals.update({
                    'debit': vals['credit'],
                    'credit': vals['debit'],
                    'partner_id': collector_id,
                    'account_id': rev_account_id,
                })
                moves[journal][collector_id]['lines'].append([0, 0, nvals])
            else:
                moves[journal][collector_id][ttype] += credit - debit


        #return move_lines, tcash, tcheck
        return res







#
