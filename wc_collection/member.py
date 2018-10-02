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

class Member(models.Model):
    _inherit = "wc.member"

    insurance_ids = fields.One2many('wc.insurance.collectible', 'member_id',
        track_visibility='onchange', string='Insurance',
        readonly=True, domain=[('state','=','confirmed')])
