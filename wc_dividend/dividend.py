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
from odoo.tools.misc import xlwt
import logging
import time
import base64
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Dividend(models.Model):
    _name = "wc.dividend"
    _description = "Dividend Distribution"
    _inherit = "mail.thread"
    _order = "date1 desc"

    def get_year(self):
        dt = fields.Date.from_string(fields.Date.context_today(self))
        dt -= relativedelta(years=1)
        return dt.strftime("%Y")

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.dividend'))

    name = fields.Char("Year / Name",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        default=get_year,
        required=True)

    date1 = fields.Date("Date From",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        default=lambda self: "%s-01-01" % self.get_year(),
        required=True)

    date2 = fields.Date("Date To",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        default=lambda self: "%s-12-31" % self.get_year(),
        required=True)

    dividend_pct = fields.Float("Dividend %",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        digits=(12,4))

    patronage_pct = fields.Float("Patronage %",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        digits=(12,4))

    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('posted', 'Posted'),
        ], 'State', default="draft",
        readonly=True, track_visibility='onchange')

    note = fields.Text('Notes', track_visibility='onchange')

    excel_data = fields.Binary('Excel File', compute='gen_excel_file')

    line_ids = fields.One2many('wc.dividend.line', 'dividend_id',
        readonly=True, string='Lines')

    @api.multi
    @api.depends('date1','date2','line_ids','state')
    def gen_excel_file(self):

        fmt_bold_left = xlwt.easyxf('font: bold on')
        fmt_bold_right = xlwt.easyxf('font: bold on; align: horiz right')
        fmt_right = xlwt.easyxf('align: horiz right')
        fmt_currency = xlwt.easyxf(num_format_str="#,##0.00")
        fmt_integer= xlwt.easyxf(num_format_str="#,##0")

        for d in self:
            wb = xlwt.Workbook()
            ws = wb.add_sheet(d.name)

            for i in range(2, 10):
                ws.col(i).width = 256 * 15
            ws.col(0).width = 256 * 15
            ws.col(1).width = 256 * 45

            d1 = fields.Date.from_string(d.date1)
            d2 = fields.Date.from_string(d.date2)

            ri = 0
            ci = 0
            ws.write(ri, 0, "DIVIDEND AND PATRONAGE COMPUTATION", fmt_bold_left)
            ri += 1
            ws.write(ri, 0, d.company_id.name, fmt_bold_left)

            ri = 0
            ws.write(ri, 3, "Date From:", fmt_bold_left)
            ws.write(ri, 4, d1, xlwt.easyxf('align: horiz right', num_format_str="mm/dd/yyyy"))
            ws.write(ri, 6, "Dividend %:", fmt_bold_left)
            ws.write(ri, 7, d.dividend_pct, xlwt.easyxf(num_format_str="#,##0.0000"))

            ri += 1
            ws.write(ri, 3, "Date To:", fmt_bold_left)
            ws.write(ri, 4, d2, xlwt.easyxf('align: horiz right', num_format_str="mm/dd/yyyy"))
            ws.write(ri, 6, "Patronage %:", fmt_bold_left)
            ws.write(ri, 7, d.patronage_pct, xlwt.easyxf(num_format_str="#,##0.0000"))

            headers = [
                ["Member ID",   fmt_bold_left],
                ["Member",      fmt_bold_left],
                ["Memb. Date",  fmt_bold_left],
                ["CBU",         fmt_bold_right],
                ["Days",        fmt_bold_right],
                ["Dividend",    fmt_bold_right],
                ["Loan Count",  fmt_bold_right],
                ["Patronage",   fmt_bold_right],
            ]

            ri += 2
            ci = 0
            for h in headers:
                ws.write(ri, ci, h[0], h[1])
                ci += 1

            for ln in d.line_ids:
                ri += 1
                ws.write(ri, 0, ln.member_code)
                ws.write(ri, 1, ln.member_id.name)
                mdt = fields.Date.from_string(ln.membership_date)
                ws.write(ri, 2, mdt, xlwt.easyxf(num_format_str="mm/dd/yyyy"))
                ws.write(ri, 3, ln.cbu_amount, fmt_currency)
                ws.write(ri, 4, ln.days, fmt_integer)
                ws.write(ri, 5, ln.dividend, fmt_currency)
                ws.write(ri, 6, ln.loan_count, fmt_integer)
                ws.write(ri, 7, ln.patronage, fmt_currency)

            outputStream = StringIO()
            wb.save(outputStream)
            d.excel_data = base64.encodestring(outputStream.getvalue())
            outputStream.close()


    @api.multi
    def confirm(self):
        for d in self:
            if d.state=='draft':
                d.gen_lines()
                d.state = 'confirmed'

    @api.multi
    def back_to_draft(self):
        for d in self:
            if d.state=='confirmed':
                d.state = 'draft'
                d.line_ids.unlink()

    @api.multi
    def gen_lines(self):
        for d in self:
            d.line_ids.unlink()
            members = self.env['wc.member'].search([
                '&',
                    ('is_approved','=',True),
                    '&',
                        ('member_type','=','regular'),
                        '|',
                            ('membership_end_date','>=',d.date2),
                            ('membership_end_date','=',False),

            ])
            lines = []
            for m in members:
                for cbu in m.cbu_account_ids:
                    cbu_amount = cbu.get_balance_at_date(cbu.id, d.date2)

                    if m.membership_date==False or m.membership_date<=d.date1:
                        days = 365
                    else:
                        d1 = fields.Date.from_string(m.membership_date)
                        d2 = fields.Date.from_string(d.date2)
                        days = max((d2-d1).days + 1, 0)

                    dividend = round(cbu_amount * d.dividend_pct * days / 36500.0, 2)

                    #get number of loans
                    loans = self.env['wc.loan'].search([
                        ('member_id','=',m.id),
                        ('state','not in',['draft','cancelled']),
                        ('date','>=',d.date1),
                        ('date','<=',d.date2),
                    ])
                    loan_count = len(loans)
                    if loan_count:
                        patronage = round(cbu_amount * d.patronage_pct * days / 36500.0, 2)
                    else:
                        patronage = 0.0

                    #_logger.debug("**gen_lines: cbu=%s div=%s pat=%s", cbu_amount, dividend, patronage)
                    if dividend > 0.0 or patronage > 0.0:
                        lines.append((0, 0, {
                            'member_id': m.id,
                            'cbu_amount': cbu_amount,
                            'days': days,
                            'dividend': dividend,
                            'loan_count': loan_count,
                            'patronage': patronage,
                        }))

            if lines:
                d.line_ids = lines

    @api.multi
    def download_as_excel(self):
        self.ensure_one()
        if not self.line_ids:
            raise Warning(_("No dividend distribution computed."))
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.dividend/%s/excel_data/output.xls?download=true' % self.id,
        }


class DividendLines(models.Model):
    _name = "wc.dividend.line"
    _description = "Dividend Calculation"
    _order = "name desc"

    dividend_id = fields.Many2one('wc.dividend', string='Dividend Distribution',
        index=True, required=True, ondelete="cascade")

    name = fields.Char(compute="_get_name")
    #share_type = fields.Selection(related='dividend_id.share_type')

    member_id = fields.Many2one('wc.member', string='Member',
        domain=[('is_approved','=',True)],
        required=True)

    member_code = fields.Char("Member ID", related="member_id.code")
    membership_date = fields.Date("Membership Date", related="member_id.membership_date")

    cbu_amount = fields.Float("Share Capital / CBU",digits=(12,2))
    days = fields.Integer("Days")
    dividend = fields.Float(digits=(12,2))
    loan_count = fields.Integer("Loan Count")
    patronage = fields.Float(digits=(12,2))

    note = fields.Text('Notes')

    @api.model
    def compute_dividend(self):
        amount = round(self.balance * 0.1, 2)

    @api.multi
    @api.depends(
        'member_id',
        'member_id.name',
    )
    def _get_name(self):
        for ln in self:
            ln.name = "%s [%s]" % (
                ln.member_id.name,
                ln.member_id.code,
            )

#
