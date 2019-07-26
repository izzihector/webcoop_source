
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
    



