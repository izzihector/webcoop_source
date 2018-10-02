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
import time

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Posting(models.Model):
    _inherit = "wc.posting"

    @api.multi
    def set_draft(self):
        for rec in self:
            for m in rec.move_ids:
                if m.state!='draft':
                    raise Warning(_("Cannot set back to draft posting with posted Journal Entries.\nCancel the entries first before setting to draft."))
            if rec.state=='posted':
                rec.state = 'draft'

class Collections(models.Model):
    _inherit = "wc.collection"

    name = fields.Char("Reference/OR#", readonly=False, states={})



#
