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

class CollectionDetail(models.Model):
    _inherit = "wc.collection.line"

    #insurance
    posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        required=False, readonly=True, ondelete="set null")

    #other collection
    oc_posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        required=False, readonly=True, ondelete="set null")


class Collections(models.Model):
    _inherit = "wc.collection"

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    date = fields.Date(default=get_first_open_date, states={})
    cancellable = fields.Boolean(compute="compute_cancellable")
    posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        readonly=True, ondelete="set null")

    @api.multi
    @api.depends('date','line_ids','line_ids.amount','line_ids.posting_id')
    def compute_cancellable(self):
        for coll in self:
            if coll.date != self.get_first_open_date():
                cancellable = False
            else:
                cancellable = True
                for ln in coll.line_ids:
                    if ln.amount!=0.0 and ln.posting_id:
                        cancellable = False
                        break
            coll.cancellable = cancellable

    @api.multi
    def reverse_collection(self):
        for coll in self:

            if coll.state!='confirmed':
                raise Warning(_("You can only reverse a confirmed collection."))

            if coll.create_uid.id != self.env.user.id:
                raise Warning(_("Only user %s can reverse this entry.") % coll.create_uid.name)

            lines = []
            insurance_ids = []
            oc_payment_ids = []
            for ln in coll.line_ids:
                if ln.loan_payment_id:
                    if not ln.loan_payment_id.is_reversed:
                        ln.loan_payment_id.reverse_payment()
                    vals = {
                        'sequence': ln.sequence,
                        'name': 'Reverse %s' % (ln.name),
                        'collection_type': 'view',
                        'amount': -ln.amount,
                        'is_reversed': True,
                        'state': 'confirmed',
                    }
                    lines.append([0, 0, vals])
                if ln.account_id:
                    vals = {
                        'sequence': ln.sequence,
                        'name': 'Reverse %s' % (ln.name),
                        'collection_type': 'view',
                        'amount': -ln.amount,
                        'is_reversed': True,
                        'state': 'confirmed',
                    }
                    lines.append([0, 0, vals])
                if ln.insurance_id and ln.amount!=0.0:
                    insurance_ids.append(ln)
                if ln.collection_type=='others' and ln.amount!=0.0:
                    oc_payment_ids.append(ln)

            if insurance_ids:
                for ln in insurance_ids:
                    vals = {
                        #'collection_id' : coll2.id,
                        'sequence': ln.sequence,
                        'name': ln.name, #'Reverse %s' % (ln.name),
                        'insurance_id': ln.insurance_id.id,
                        'insurance_collectible_id': ln.insurance_collectible_id.id,
                        'collection_type': ln.collection_type,
                        'amount': -ln.amount,
                        'is_reversed': True,
                        'state': 'confirmed',
                    }
                    lines.append([0, 0, vals])

            if oc_payment_ids:
                for ln in oc_payment_ids:
                    vals = {
                        #'collection_id' : coll2.id,
                        'sequence': ln.sequence,
                        'name': ln.name, #'Reverse %s' % (ln.name),
                        'collection_type': ln.collection_type,
                        'amount': -ln.amount,
                        'gl_account_id': ln.gl_account_id.id,
                        'is_reversed': True,
                        'state': 'confirmed',
                    }
                    lines.append([0, 0, vals])

            _logger.debug("reverse_collection: lines=%s", lines)
            if lines:
                coll2 = self.create({
                    'company_id': coll.company_id.id,
                    'name': "%s reversed" % coll.name,
                    'code': coll.code,
                    'member_id': coll.member_id.id,
                    'state': 'reversed',
                    'in_branch': coll.in_branch,
                    'line_ids': lines,
                })

            coll.cancel_collection_account()
            coll.state = 'reversed'


class Posting(models.Model):
    _inherit = "wc.posting"

    oc_payment_ids = fields.One2many('wc.collection.line', 'oc_posting_id',
         readonly=True, string='Others Payments')

    @api.multi
    def set_draft(self):
        self.clear_collection_posting()
        return super(Posting, self).set_draft()

    @api.multi
    def clear_collection_posting(self):
        for p in self:
            colls = self.env['wc.collection'].sudo().search([
                ('company_id','=',p.company_id.id),
                ('date','=',p.name),
                ('state','=','confirmed'),
            ])
            colls.write({'posting_id': False})
            for pay in p.sudo().oc_payment_ids:
                pay.oc_posting_id = False

    @api.multi
    def add_details(self):
        self.clear_collection_posting()
        for p in self:
            colls = self.env['wc.collection'].sudo().search([
                ('company_id','=',p.company_id.id),
                ('date','=',p.name),
                ('state','in',['confirmed','reversed']),
            ])
            colls.write({'posting_id': p.id})

            payment_ids = self.env['wc.collection.line'].sudo().search([
                ('company_id','=',p.company_id.id),
                ('date','=',p.name),
                ('state','=','confirmed'),
                ('collection_type','=','others'),
                ('amount','!=',0.0),
            ])
            _logger.debug("oc add_details: res=%s", payment_ids)
            for pay in payment_ids:
                pay.oc_posting_id = p.id

        return super(Posting, self).add_details()

    @api.model
    def get_move_lines(self, rec, moves):
        res = super(Posting, self).get_move_lines(rec, moves)
        jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()
        date = rec.name

        for ocp in rec.oc_payment_ids:
            collector_id = ocp.collection_id.create_uid.partner_id.id

            if ocp.collection_id and not ocp.collection_id.in_branch:
                journal = 'jv'
                journal_id = jv_journal_id.id
                ttype = 'tncash'
                rev_account_id = cr_journal_id.default_credit_account_id.id
            else:
                journal = 'cr'
                journal_id = cr_journal_id.id
                ttype = 'tcash'
                rev_account_id = rec.company_id.cash_account_id.id,

            if collector_id not in moves[journal]:
                moves[journal][collector_id] = {
                    'lines': [],
                    'tcash': 0.0,
                    'tcheck': 0.0,
                    'tncash': 0.0,
                    'name': ocp.collection_id.create_uid.name,
                }

            debit, credit = to_dr_cr(-ocp.amount)
            #tcash += ocp.amount

            account_id = ocp.gl_account_id.id
            if not account_id:
                raise Warning( _("Error!\nGL Account for other payment type %s is not set.") % ocp.name)

            or_number = ocp.collection_id.name and (" OR#%s" % ocp.collection_id.name) or ""
            vals = {
                'journal_id': journal_id,
                'date': date,
                'account_id': account_id,
                'name': "%s%s" % (ocp.name, or_number),
                'partner_id': ocp.member_id.partner_id.id,
                'debit': debit,
                'credit': credit,
            }
            _logger.debug("*add ocp move: %s", vals)

            moves[journal][collector_id]['lines'].append([0, 0, vals])

            if ocp.is_reversed:
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
