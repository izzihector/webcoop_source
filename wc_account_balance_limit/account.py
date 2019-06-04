
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class AccountType(models.Model):
    _inherit = "wc.account.type"
    balance_roof_limit = fields.Float('Balance Roof Limit',help='Cannot deposit over this balance.If this field is empty , no limit.')


class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"

    @api.multi
    def confirm(self):
        for r in self:
            balance_limit = r.account_id.account_type_id.balance_roof_limit
            if r.state == 'draft' and balance_limit > 0.0:
                newbal = r.account_id.balance + r.deposit - r.withdrawal
                if newbal > balance_limit:
                    raise ValidationError(_("You cannot deposit more than balance roof limit" \
                                            "(limit = %s , but you try new_balance = %s)") % (balance_limit,newbal))
        return super(AccountTransaction, self).confirm()
