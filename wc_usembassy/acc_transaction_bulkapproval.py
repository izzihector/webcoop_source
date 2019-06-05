
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import UserError,ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"
    bulk_approve_id = fields.Many2one('wc.usembassy.acc.transaction.bulkapproval')

class AccTranBulkApproval(models.Model):
    _name = "wc.usembassy.acc.transaction.bulkapproval"
    selected_ids = fields.One2many("wc.account.transaction","bulk_approve_id")
    selected_ids_count =fields.Float(string="Selected Transaction Count")
    deposit_total = fields.Float("Deposit Total")
    withdraw_total = fields.Float("Withdraw Total")
        
    @api.model
    def default_get(self, fields):
        rec = super(AccTranBulkApproval, self).default_get(fields)
        _logger.debug("AccTranBulkApproval: default_get")
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(_("Error:No data selected."))
        if active_model != 'wc.account.transaction':
            raise UserError(_("Error:The expected model for this action is 'wc.account.transaction'. The provided one is '%d'.") % active_model)

        trans = self.env[active_model].browse(active_ids)

        total_deposit = 0
        total_withdrawal = 0
        cnt = 0
        current_date = self.env['wc.posting'].get_first_open_date(self.env.user.company_id.id)
        for tran in trans:
            if tran.state not in ['draft']:
                raise UserError(_("You can only draft transaction for bulk approval."))
            if tran.date != current_date:
                raise UserError(_("Including trans which transaction date doesn't match current opened date."))

            cnt += 1
            total_deposit += tran.deposit 
            total_withdrawal += tran.withdrawal

        rec.update({
            'selected_ids': [[6,0,active_ids]],
            'deposit_total': total_deposit,
            'withdraw_total': total_withdrawal,
            'selected_ids_count': cnt
        })
        return rec
    

    @api.multi
    def bulk_approve(self):
        max_cnt = 100
        cnt = 0           
        if self.selected_ids_count > max_cnt:
            raise Warning(_("Only %s can be approved with this bulk approval."))
            
        for r in self.selected_ids:
            cnt = cnt +1
            if cnt > max_cnt:
                break
            r.confirm()
        