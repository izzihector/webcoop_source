from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Member(models.Model):
    _inherit = "wc.member"

    @api.multi
    @api.depends('loan_ids')
    def compute_loan(self):

        for r in self:
            loans = 0
            for loan in r.loan_ids:
                if loan.state not in ['draft','cancelled','closed']:
                    loans += 1
            for loan in r.comaker_loan_ids:
                if loan.member_id.id!=r.id and loan.state not in ['draft','cancelled','closed']:
                    loans += 1
            r.loan_count = loans
        
