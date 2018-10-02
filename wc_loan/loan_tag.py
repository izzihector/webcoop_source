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

class LoanTags(models.Model):

    _name = "wc.loan.tag"
    _description = "Loan Tags"

    name = fields.Char(string="Loan Tag", required=True)
    color = fields.Integer(string='Color Index')
    loan_ids = fields.Many2many('wc.loan', 'loan_tag_rel', 'tag_id', 'loan_id', string='Loans')
    note =  fields.Text("Notes")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Loan tag already exists !"),
    ]
