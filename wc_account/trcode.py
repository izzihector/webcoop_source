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

class TransactionCodes(models.Model):
    _name = "wc.tr.code"
    _inherit = "mail.thread"
    _description = "Transaction Codes"
    _order = "trans_type, code"

    code = fields.Char('Code', required=True, track_visibility='onchange')
    description = fields.Char(track_visibility='onchange', required=True)
    name = fields.Char('Name', compute="compute_name", store=True)

    gl_posting = fields.Selection([
        ('cr', 'CR'),
        ('dr', 'DR'),
    ], 'GL Posting', track_visibility='onchange')

    trans_type = fields.Selection([
        ('cbu', 'CBU'),
        ('sa', 'SA'),
        ('td', 'TD'),
        ('ib', 'IB'),
    ], 'Type', track_visibility='onchange', required=True)

    is_deposit = fields.Boolean("Deposit", default=False)
    is_withdrawal = fields.Boolean("Withdrawal", default=False)

    note = fields.Text('Notes', track_visibility='onchange')

    _sql_constraints = [
        ('unique_code', 'unique(code, trans_type)', 'The transaction code must be unique for each type!')
    ]

    @api.multi
    @api.depends('code','description')
    def compute_name(self):
        for r in self:
            r.name = "%s - %s" % (r.code, r.description)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        records = self.browse()
        if name:
            records = self.search([('code', 'ilike', name)] + args, limit=limit)
        if not records:
            records = self.search([('name', operator, name)] + args, limit=limit)
        return records.name_get()

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        self.env.cr.execute("SELECT MAX(id) as mx FROM wc_tr_code")
        res = self.env.cr.fetchone()[0] or 0
        default = dict(
            default or {},
            code= '%s copy#%d' % (self.code, res+1),
            description=_('%s (copy)') % self.description,
        )
        return super(TransactionCodes, self).copy(default)


#
