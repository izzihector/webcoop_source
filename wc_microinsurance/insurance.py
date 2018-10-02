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

class InsuranceType(models.Model):
    _name = "wc.insurance.type"
    _description = "Insurance Type"
    _inherit = [ 'mail.thread' ]
    _order = "name"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.insurance'))

    name = fields.Char("Name", track_visibility='onchange')
    amount = fields.Float("Enrollment Amount", digits=(12,2), track_visibility='onchange')
    active = fields.Boolean(default=True, track_visibility='onchange')
    note = fields.Text('Notes', track_visibility='onchange')


class Insurance(models.Model):
    _name = "wc.insurance"
    _description = "Insurance"
    _inherit = [ 'mail.thread' ]
    _order = "date_start desc, name"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.insurance'))

    name = fields.Char("Reference", required=True, track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]})

    amount = fields.Float("Enrollment Amount", digits=(12,2), track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]})

    type_id = fields.Many2one('wc.insurance.type', 'Type', required=True,
        ondelete='restrict', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]})

    date_start = fields.Date("Date Start", required=True, track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]}, index=True)

    date_end = fields.Date("Date End", required=True, track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]}, index=True)

    member_ids = fields.Many2many('wc.member', string='Enrolled Members',
        domain=[('is_approved','=',True)],
        track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]})

    active = fields.Boolean(default=True, track_visibility='onchange')

    state = fields.Selection([
        ('draft','Draft'),
        ('cancelled','Cancelled'),
        ('confirmed','Confirmed'),
    ], string='State', default=lambda self: 'draft',
        track_visibility='onchange', readonly=True)

    note = fields.Text('Notes', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]})

    @api.onchange('type_id')
    def oc_type_id(self):
        for r in self:
            r.amount = r.type_id.amount

    @api.multi
    def toggle_active(self):
        for r in self:
            r.active = not r.active

    @api.one
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.date_start > self.date_end:
            raise ValidationError(_("Date End must be after Date Start."))

    @api.multi
    def cancel(self):
        for r in self:
            r.state = 'cancelled'

    @api.multi
    def back_to_draft(self):
        for r in self:
            r.state = 'draft'

    @api.multi
    def gen_collectibles(self):
        for r in self:
            if len(r.member_ids)>0 and r.amount>0:
                coll_member_ids = set()
                for c in r.collectible_ids:
                    if c.amount==0.0 and c.amount_paid==0.0:
                        c.unlink()
                    else:
                        coll_member_ids.add(c.member_id.id)
                _logger.debug("coll members: %s", coll_member_ids)
                for m in r.member_ids:
                    if m.id not in coll_member_ids:
                        r.collectible_ids.create({
                            'insurance_id': r.id,
                            'member_id': m.id,
                            'amount': r.amount,
                        })

    @api.multi
    def confirm(self):
        self.gen_collectibles()
        for r in self:
            if len(r.member_ids)>0 and r.amount>0:
                r.state = 'confirmed'

class InsuranceCollectible(models.Model):
    _name = "wc.insurance.collectible"
    _description = "Insurance Collectibles"
    _order = "id desc"

    insurance_id = fields.Many2one('wc.insurance', 'Reference', readonly=True, ondelete='restrict')
    type_id = fields.Many2one(related="insurance_id.type_id")
    date_start = fields.Date(related="insurance_id.date_start")
    date_end = fields.Date(related="insurance_id.date_end")
    member_id = fields.Many2one('wc.member', 'Member', readonly=True, ondelete='restrict')
    member_code = fields.Char(related="member_id.code")
    amount = fields.Float("Premium Amount", digits=(12,2))
    note = fields.Text('Notes')
    state = fields.Selection(related="insurance_id.state", store=True)
    current = fields.Boolean("Current", compute="compute_current")

    #amount_paid = fields.Float("Amount Paid", digits=(12,2), compute="compute_paid")
    #paid = fields.Boolean("Paid", compute="compute_paid")
    #payment_ids = fields.One2many('wc.collection.line', 'insurance_collectible_id',
    #    readonly=True, string='Payments')

    @api.depends('date_start','date_end')
    def compute_current(self):
        #today = fields.Date.from_string(fields.Date.context_today(self))
        today = fields.Date.context_today(self)
        for r in self:
            r.current = today>=r.date_start and today<=r.date_end
