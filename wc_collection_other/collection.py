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

class Collections(models.Model):
    _inherit = "wc.collection"

    new_payment_type_id = fields.Many2one('wc.oc.payment.type', string='Others / Misc.', ondelete="set null")
    oc_amount = fields.Float("Amount", digits=(12,2))
    #partner_id = fields.Many2one('res.partner', string="Partner")

    @api.multi
    def add_others(self):
        for coll in self:
            if coll.oc_amount!=0.0 and coll.new_payment_type_id:
                vals = {
                    'collection_id': coll.id,
                    'gl_account_id': coll.new_payment_type_id.gl_account_id.id,
                    'sequence': 5000000,
                    'name': coll.new_payment_type_id.name,
                    'collection_type': 'others',
                    'amount': coll.oc_amount,
                    #'partner_id': coll.partner_id.id,
                }
                _logger.debug("add_others: %s", vals)
                #coll.line_ids = [0, 0, vals]
                coll.line_ids.create(vals)
                coll.oc_amount = 0.0
                coll.new_payment_type_id = False
                #coll.partner_id = False


class CollectionDetail(models.Model):
    _inherit = "wc.collection.line"
    gl_account_id = fields.Many2one('account.account', string='GL Account', ondelete="set null")
    #partner_id = fields.Many2one('res.partner', string="Partner")
