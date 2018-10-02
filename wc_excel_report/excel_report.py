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

class ExcelReport(models.Model):
    _name = 'wc.excel.report'
    _description = 'Excel Report'
    _inherit = "mail.thread"
    _order = "name"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        track_visibility='onchange',
        default=lambda self: self.env['res.company']._company_default_get('wc.excel.report'))

    name = fields.Char("Report Name", required=True, track_visibility='onchange')

    report_type = fields.Selection([
            ('jsummary', 'Summary (new)'),
            ('detailed', 'Detailed'),
            ('summary', 'Summary'),
        ], 'Report Type', required=True, default='summary', track_visibility='onchange')

    journal_ids = fields.Many2many('account.journal', string='Journals')
    account_ids = fields.Many2many('account.account', string='Accounts')

    prepared_by = fields.Char("Prepared By", track_visibility='onchange')
    checked_by = fields.Char("Checked By", track_visibility='onchange')
    approved_by = fields.Char("Approved By", track_visibility='onchange')

    template_data = fields.Binary('Template', required=True, track_visibility='onchange')
    template_filename = fields.Char('Filename', track_visibility='onchange')

    note = fields.Text('Notes', track_visibility='onchange')
