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

class OtherCollection(models.Model):
    _name = "wc.oc.payment.type"
    _description = "Other Collection Payment Types"
    _inherit = [ 'mail.thread' ]
    _order = "name"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.oc.payment.type'))
    name = fields.Char("Name", required=True, track_visibility='onchange')
    gl_account_id = fields.Many2one('account.account', string='GL Account', ondelete="set null")
    note = fields.Text(string='Notes', track_visibility='onchange')




#
