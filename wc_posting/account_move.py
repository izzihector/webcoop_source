# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import api, fields, models
from odoo import tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class AccountMove(models.Model):
    _inherit = "account.move"

    posting_id = fields.Many2one('wc.posting', string='Posting Ref', readonly=True, ondelete="set null")

    #remove later
    daily_posting = fields.Boolean("Daily Posting", readonly=True)

    @api.multi
    def post_nocheck(self):
        return super(AccountMove, self).post()

    @api.multi
    def post(self):
        for m in self:
            if m.posting_id and self.env.user.id!=SUPERUSER_ID:
                raise Warning(_("Cannot post journal created from Daily Posting. Use Daily Posting menu to post."))
        return super(AccountMove, self).post()
