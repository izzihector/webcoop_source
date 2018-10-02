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

class Partner(models.Model):
    _inherit = "res.partner"

    address2 = fields.Char("Address", compute="compute_address2")

    @api.depends(lambda self: self._display_address_depends())
    def compute_address2(self):
        for partner in self:
            partner.address2 = partner._display_address(without_company=True)
