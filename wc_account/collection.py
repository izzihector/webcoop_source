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

class CollectionDetail(models.Model):
    _inherit = "wc.collection.line"
    account_id = fields.Many2one('wc.account', string='Account', readonly=True, ondelete="restrict")


class Collections(models.Model):
    _inherit = "wc.collection"

    @api.model
    def get_lines(self, c):
        lines = super(Collections, self).get_lines(c)
        _logger.debug("**get_lines account: member=%s", c.member_id.name)
        if c.member_id:
            seq = 3000
            accounts = {}
            for acct in c.member_id.cbu_account_ids:
                accounts[acct.id] = {
                    'collection_id' : c.id,
                    'sequence': seq,
                    'name': 'Deposit %s %s' % (acct.code, acct.account_type_id.description),
                    'account_id': acct.id,
                    #'code': 'cbu',
                    'collection_type': 'deposit',
                }
                seq += 1
                _logger.debug("**get_lines account: acct=%s", c.member_id.name)

            for acct in c.member_id.account_ids:
                if (acct.account_type!='td') and (acct.id not in accounts) and (acct.state in ['open','dormant']):
                    accounts[acct.id] = {
                        'collection_id' : c.id,
                        'sequence': seq,
                        'name': 'Deposit %s %s' % (acct.code, acct.account_type_id.description),
                        'account_id': acct.id,
                        #'code': 'sa',
                        'collection_type': 'deposit',
                    }
                    seq += 1
                    _logger.debug("**get_lines account: acct=%s", c.member_id.name)

            for acct in c.member_id.joint_account_ids:
                if (acct.id not in accounts) and (acct.state in ['open','dormant']):
                    accounts[acct.id] = {
                        'collection_id' : c.id,
                        'sequence': seq,
                        'name': 'Deposit %s %s (joint)' % (acct.code, acct.account_type_id.description),
                        'account_id': acct.id,
                        #'code': 'sa',
                        'collection_type': 'deposit',
                    }
                    seq += 1
                    _logger.debug("**get_lines account: acct=%s", c.member_id.name)

            for k in accounts:
                _logger.debug("**create: %s", accounts[k])
                #c.line_ids.create(accounts[k])
                lines.append( (0, False, accounts[k]))

        _logger.debug("**get_lines account: %s", lines)
        return lines

    @api.model
    def Xgen_line_account(self, c, cbu_due=0.0, savings_due=0.0):

        #res = super(Collections, self).gen_lines()

        if c.member_id and c.id:
            for l in c.line_ids:
                if l.collection_type == 'deposit' or not l.collection_type:
                    l.write({
                        'name': 'Deleted',
                        'amount': 0.0,
                        'is_deleted': True,
                    })
            seq = 3000
            accounts = {}
            for acct in c.member_id.cbu_account_ids:
                accounts[acct.id] = {
                    'collection_id' : c.id,
                    'sequence': seq,
                    'name': 'Deposit %s %s' % (acct.code, acct.account_type_id.description),
                    'account_id': acct.id,
                    'code': 'cbu',
                    'amount_due': cbu_due,
                    'collection_type': 'deposit',
                }
                cbu_due = 0.0,
                seq += 1

            for acct in c.member_id.account_ids:
                if (acct.account_type!='td') and (acct.id not in accounts) and (acct.state in ['open','dormant']):
                    accounts[acct.id] = {
                        'collection_id' : c.id,
                        'sequence': seq,
                        'name': 'Deposit %s %s' % (acct.code, acct.account_type_id.description),
                        'account_id': acct.id,
                        'code': 'sa',
                        'amount_due': savings_due,
                        'collection_type': 'deposit',
                    }
                    savings_due = 0.0
                    seq += 1

            for acct in c.member_id.joint_account_ids:
                if (acct.id not in accounts) and (acct.state in ['open','dormant']):
                    accounts[acct.id] = {
                        'collection_id' : c.id,
                        'sequence': seq,
                        'name': 'Deposit %s %s (joint)' % (acct.code, acct.account_type_id.description),
                        'account_id': acct.id,
                        'code': 'sa',
                        'collection_type': 'deposit',
                    }
                    seq += 1

            for k in accounts:
                _logger.debug("**create: %s", accounts[k])
                c.line_ids.create(accounts[k])

    @api.multi
    def confirm(self):
        trcode_cbu = self.env.ref('wc_account.tr_deposit')
        if not trcode_cbu:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','cbu'),
                ('is_deposit','=',True),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No CBU deposit transaction type present."))
            trcode_cbu = res[0]

        trcode_csd = self.env.ref('wc_account.tr_csd')
        if not trcode_csd:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','sa'),
                ('is_deposit','=',True),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No account deposit transaction type present."))
            trcode_csd = res[0]

        res = super(Collections, self).confirm()

        #add to account transactions
        trans_obj = self.env['wc.account.transaction']
        for rec in self:
            for line in rec.line_ids:
                if line.collection_type=='deposit' and line.amount!=0.0 and not line.is_deleted:
                    if line.account_id.account_type=='cbu':
                        trtype_id = trcode_cbu.id
                    else:
                        trtype_id = trcode_csd.id
                    res = trans_obj.create({
                        'account_id': line.account_id.id,
                        'date': line.date,
                        'deposit': line.amount,
                        'trcode_id': trtype_id,
                        'reference': rec.name, #'collection',
                        'collection_id': rec.id,
                        #'state': 'confirmed',
                    })
                    res.confirm()
        #return res

    @api.multi
    def Xcancel(self):
        self.cancel_collection_account()
        return super(Collections, self).cancel()

    @api.multi
    def cancel_collection_account(self):
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

        #add to account transactions
        dt = fields.Date.context_today(self)
        trans_obj = self.env['wc.account.transaction']
        for rec in self:
            for line in rec.line_ids:
                if line.collection_type=='deposit' and line.amount!=0.0 and not line.is_deleted:
                    if line.account_id.account_type=='cbu':
                        trtype_id = trcode_cbu.id
                    else:
                        trtype_id = trcode_sa.id
                    res = trans_obj.create({
                        'account_id': line.account_id.id,
                        'withdrawal': line.amount,
                        'trcode_id': trtype_id,
                        'reference': 'reverse collection',
                        'collection_id': rec.id,
                    })
                    res.confirm()
                    res.approve()
