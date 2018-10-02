# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class MemberDependents(models.Model):
    _name = "wc.member.dependent"
    _description = "Member Dependents"
    _order = "name"

    member_id = fields.Many2one('wc.member', 'Member', readonly=True, ondelete='restrict')
    name = fields.Char(required=True)
    relationship = fields.Char()
    birthday = fields.Date(track_visibility='onchange')
    age = fields.Float(compute="_get_age", digits=(12,2))
    contact = fields.Char('Contact No.')
    address = fields.Char('Address')
    note = fields.Text('Notes')

    @api.depends('birthday')
    def _get_age(self):
        today = fields.Date.from_string(fields.Date.context_today(self))
        days_in_year = 365.2425
        for r in self:
            if r.birthday:
                r.age = (today - fields.Date.from_string(r.birthday)).days / days_in_year


class Member(models.Model):
    _inherit = "wc.member"

    dependent_ids = fields.One2many('wc.member.dependent', 'member_id',
        track_visibility='onchange', string='Dependents')
