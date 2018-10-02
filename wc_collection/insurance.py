# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Insurance(models.Model):
    _inherit = "wc.insurance"

    collectible_ids = fields.One2many('wc.insurance.collectible', 'insurance_id',
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', string='Collectibles')

    payment_ids = fields.One2many('wc.collection.line', 'insurance_id',
        readonly=True, string='Payments', domain=[('state','!=','draft')])

    @api.multi
    def cancel(self):
        for r in self:
            for c in r.collectible_ids:
                if c.amount_paid > 0.0:
                    raise Warning(_("Cannot cancel microinsurance that has payments."))
        return super(Insurance, self).cancel()


class InsuranceCollectible(models.Model):
    _inherit = "wc.insurance.collectible"

    amount_paid = fields.Float("Amount Paid", digits=(12,2), compute="compute_paid")
    paid = fields.Boolean("Paid", compute="compute_paid")
    payment_ids = fields.One2many('wc.collection.line', 'insurance_collectible_id',
        readonly=True, string='Payments')

    @api.multi
    @api.depends('amount','payment_ids','payment_ids.state','payment_ids.amount')
    def compute_paid(self):
        for r in self:
            tpaid = 0.0
            for p in r.payment_ids:
                if p.state=='confirmed':
                    tpaid += p.amount
            r.amount_paid = tpaid
            if tpaid>=r.amount:
                r.paid = True
            else:
                r.paid = False
