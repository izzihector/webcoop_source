
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class LoanDetail(models.Model):
    _inherit = "wc.loan.detail"
    
#     reconcile_search_ids = fields.Many2many()

    payment_reconciliation_line_id = fields.Many2one('wc.loan.payment.reconciliation.line', 'Reference', ondelete='restrict')
    member_id = fields.Many2one('wc.member',related='loan_id.member_id')

#     


