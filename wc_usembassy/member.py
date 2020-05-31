
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import UserError,ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Member(models.Model):
    _inherit = "wc.member"
    division = fields.Char('Agency/Division',track_visibility='onchange')
    date_of_employement = fields.Date('USG Date of Employment',track_visibility='onchange')
    payroll_number = fields.Char('Payroll Number',track_visibility='onchange')

    employee_code = fields.Char('Employee ID',track_visibility='onchange',old_name='employee_id')
    member_age = fields.Float(compute="_get_member_age", digits=(12,2))
    ###20200530
#     fund_transfer_type = fields.Selection([('citi','CITI Bank'),('pnb','PNG'),
#                                            ('check','Check Account Number'),
#                                            ('coop','Cooperative Savings')],string="Fund Transfer")
    fund_transfer_type = fields.Selection([('citi','CITI Bank'),('pnb','PNB'),
                                           ('check','Check Account Number'),
                                           ('coop','Cooperative Savings')],string="Fund Transfer")
    fund_transfer = fields.Char()
    
    @api.depends('membership_date','membership_end_date')
    def _get_member_age(self):
        today = fields.Date.from_string(fields.Date.context_today(self))
        days_in_year = 365.2425
        for r in self:
            if r.membership_end_date:
                    tdate = fields.Date.from_string(r.membership_end_date)
            else:
               tdate = today
            if r.membership_date:
                r.member_age = (tdate - fields.Date.from_string(r.membership_date)).days / days_in_year
            else:
                r.member_age =False
 
    @api.onchange('fund_transfer_type')
    def onchange_fund_type(self):
        for r in self:
            if not r.fund_transfer_type:
                return {'value':{'fund_transfer':False}}



