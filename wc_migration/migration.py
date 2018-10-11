from odoo import api, fields, models

class ForceApproveForInitialData(models.Model):
    _name = 'wc.migration'

    @api.multi
    def initialapproveMember(self):
        records=self.env['wc.member'].search([['is_approved', '=', False]])
        records.approve_member()
        
    @api.multi
    def initialapproveSavingAndTimeDeposit(self):        
        records=self.env['wc.account'].search([['state', '=', 'draft']])
        records.approve_account()
              
    @api.multi
    def initialapproveLoan(self):        
        records=self.env['wc.loan'].search([['state', '=', 'draft']])
        records.move_to_approved()
    
    @api.multi
    def initialaccounttran(self):        
        records=self.env['wc.account.transaction'].search([['state', '=', 'draft']])
        records.confirm()
        records=self.env['wc.account.transaction'].search([['state', '=', 'for-approval']])
        records.approve()
        
        
        