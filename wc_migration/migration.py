from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)
DF = '%Y-%m-%d'
ADD_MONTHS = {
    'quarterly': 3,
    'semi-annual': 6,
    'annual': 12,
}


class ForceApproveForInitialData(models.Model):
    _name = 'wc.migration'
                
    #changed 2018 11 19 for speedup     
    @api.multi
    def initialapproveMember(self):
        #20181119 suzuki modify
        #add company id domain for getting target data , for avoiding update ohter branch data
        #add check for daily posting data existing.                
        self.check_selected_company_iscorrect()        
        records =self.env['wc.member'].search([['is_approved', '=', False],['company_id','=',self.selfDic()['com']]])        
        cbu_type_id = False
        
        max_cnt = 10000
        cnt = 0

        for rec in records:
            cnt = cnt + 1
            if cnt > max_cnt:
                break       
            mem_code = rec.code
            if not mem_code:
                if rec.company_id.branch_code:
                    prefix = '%s-' % rec.company_id.branch_code
                else:
                    prefix = ''
                mem_code = '%s%s' % (prefix, self.env['ir.sequence'].next_by_code('wc.member'))
                sql = "UPDATE wc_member "\
                      "SET approver_id=%s,"\
                      "    write_uid=%s ,"\
                      "    write_date='%s' ,"\
                      "    approval_date='%s',"\
                      "    is_approved=%s ,"\
                      "    code='%s' "\
                      "WHERE id = %s"\
                       % (self.selfDic()['uid'],
                          self.selfDic()['uid'],
                          self.selfDic()['time'],
                          self.selfDic()['date'],
                          True,
                          mem_code,
                          rec.id )

                self._cr.execute(sql)                
                _logger.debug('member approved id=%s ,mem_code=%s' % (rec.id,mem_code)) 

            if rec.member_type == 'regular':
                if not cbu_type_id:
                    res_id = self.env['wc.account.type'].search([
                     ('category', '=', 'cbu'),
                     (
                      'company_id', '=', rec.company_id.id)], limit=1)
                    if not res_id:
                        raise Warning(_('Account type CBU is missing.'))
                    cbu_type_id = res_id[0]

                #compute maturity date
                months = ADD_MONTHS.get(cbu_type_id.posting_schedule, 12)
                dt = fields.Datetime.from_string(self.selfDic()['date']) + relativedelta(months=months)
                date_maturity = dt.strftime(DF)

                sql = "INSERT INTO wc_account"\
                        " ("\
                        "  create_uid ,"\
                        "  create_date ,"\
                        "  write_uid ,"\
                        "  write_date ,"\
                        "  company_id ,"\
                        "  passbook_line ,"\
                        "  balance ,"\
                        "  date_start ,"\
                        "  date_maturity ,"\
                        "  member_id ,"\
                        "  account_type_id ,"\
                        "  account_type ,"\
                        "  state ,"\
                        "  code ,"\
                        "  name ,"\
                        "  active"\
                        " ) VALUES (%s,'%s',%s,'%s',%s,%s,%s,'%s','%s',%s,%s,'%s','%s','%s','%s',%s)"\
                        % (self.selfDic()['uid'],
                           self.selfDic()['time'], 
                           self.selfDic()['uid'],
                           self.selfDic()['time'], 
                           rec.company_id.id,
                           0,
                           0,
                           self.selfDic()['date'],
                           date_maturity,
                           rec.id , 
                           cbu_type_id.id ,
                           cbu_type_id.category ,
                           'open' ,
                           mem_code ,
                           mem_code + " - " + rec.name,
                           True )
                                                      
                self._cr.execute(sql)
                _logger.debug('account created code=%s ,name=%s' % (mem_code,mem_code + " - " + rec.name))
        
    #changed 2018 11 19 for speedup                          
    @api.multi
    def initialapproveSavingAndTimeDeposit(self):    
        self.check_selected_company_iscorrect()      
        records=self.env['wc.account'].search([['state', '=', 'draft'],['company_id','=',self.selfDic()['com']]])       
           
        max_cnt = 10000
        cnt = 0
    
        i=1
        for r in records:
            cnt = cnt +1
            if cnt > max_cnt:
                break
            if r.custom_months < 0:
                raise ValidationError(_('Cannot set custom months period to less than zero.'))
            r_state = 'open'
            if r.code == 'NONE' or not r.code:
                if r.account_type == 'cbu':
                    if r.member_id.is_approved:
                        r_code = r.member_id.code
                elif r.account_type_id.sequence_id:
                    r_code = r.account_type_id.code + '-' + r.account_type_id.sequence_id.next_by_id()
            
            sql = "UPDATE wc_account "\
                  "SET state='%s',"\
                  "    code='%s',"\
                  "    write_uid=%s ,"\
                  "    write_date='%s' "\
                  " WHERE id = %s"\
                   % (r_state,
                      r_code,
                      self.selfDic()['uid'],
                      self.selfDic()['time'],
                      r.id )
            self._cr.execute(sql)

                
    #changed 2018 11 19 for speedup    
    @api.multi
    def initialapproveLoan(self):
        self.check_selected_company_iscorrect()   
        records=self.env['wc.loan'].search([['state', '=', 'draft'],['company_id','=',self.selfDic()['com']]])
                   
        max_cnt = 500
        cnt = 0   
        
        for r in records:
            cnt = cnt +1
            if cnt > max_cnt:
                break            

            if r.state == 'draft':
                r.generate_schedule()
                
            r_code =r.code
            if r_code == 'DRAFT' or not r_code:
                r_code = r.loan_type_id.code + '-' + r.loan_type_id.sequence_id.next_by_id()
            r.gen_soa_details(r, r.date_start)
            
            sql = "UPDATE wc_loan "\
                  "SET state='%s',"\
                  "    code='%s',"\
                  "    write_uid=%s ,"\
                  "    write_date='%s' "\
                  " WHERE id = %s"\
                       % ('approved',
                          r_code,
                          self.selfDic()['uid'],
                          self.selfDic()['time'],
                          r.id )
            self._cr.execute(sql)
                    
                                         
    @api.multi
    def initialapproveLoan_onlyloan(self):
    #this is for loan approve with no amortization schedule update
    #this is used in case you create custom amortization schedule and loan detail record
        self.check_selected_company_iscorrect()   
        records=self.env['wc.loan'].search([['state', '=', 'draft'],['company_id','=',self.selfDic()['com']]])

        max_cnt=10000
        cnt =0
        
        for r in records:
            cnt = cnt+1
            if cnt > max_cnt:
                break
            
            r_code =r.code
            if r_code == 'DRAFT' or not r_code:
                r_code = r.loan_type_id.code + '-' + r.loan_type_id.sequence_id.next_by_id()

            sql = "UPDATE wc_loan "\
                  "SET state='%s',"\
                  "    code='%s',"\
                  "    write_uid=%s ,"\
                  "    write_date='%s' "\
                  " WHERE id = %s"\
                       % ('approved',
                          r_code,
                          self.selfDic()['uid'],
                          self.selfDic()['time'],
                          r.id )
            self._cr.execute(sql)
                    

    #changed 2018 11 19 for speedup    
    @api.multi
    def initialaccounttran(self):     
        records=self.env['wc.account.transaction'].search([['state', '=', 'draft']])

        max_cnt = 10000
        cnt = 0           
        for r in records:
            cnt = cnt +1
            if cnt > max_cnt:
                break          
            if r.state == 'draft':
                new_state = 'confirmed'
                context = {'ir_sequence_date': r.date}

                r_name = self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction')
                if r.trcode_id.code in ['LCKD','RCKD']:
                    new_state = 'clearing'
                elif r.trcode_id.code == 'A->D' and r.account_id.state == 'open':
                    new_state = 'for-approval'
                elif r.trcode_id.code == 'D->A' and r.account_id.state == 'dormant':
                    new_state = 'for-approval'
                elif r.trcode_id.code in ['3000','CM00','XPLT','RCHK','A->D','D->A']:
                    new_state = 'for-approval'

                #mark for approval if withdrawal more than maintaining
                if r.withdrawal>0.0 and (r.account_id.balance-r.withdrawal)<r.account_id.maintaining_balance:
                    new_state = 'for-approval'

                elif r.withdrawal >= r.account_id.account_type_id.withdrawal_limit:
                    new_state = 'for-approval'

                elif r.deposit >= r.account_id.account_type_id.deposit_limit:
                    new_state = 'for-approval'

                r_state = new_state
                r_confirm_date = fields.Datetime.now()
                
                if r_state == 'for-approval':
                    new_state = 'confirmed'
                    if r.trcode_id.code == 'D->A' and r.account_id.state == 'dormant':
                        r.account_id.state = 'open'
                    elif r.trcode_id.code == 'A->D' and r.account_id.state == 'open':
                        r.account_id.state = 'dormant'
                    r_state = new_state
                    r_confirm_date = fields.Datetime.now()
                
                sql = "UPDATE wc_account_transaction "\
                  "SET name = '%s',"\
                  "    state='%s',"\
                  "    confirm_date ='%s',"\
                  "    write_uid=%s ,"\
                  "    write_date='%s' "\
                  " WHERE id = %s"\
                       % (r_name,
                          r_state,
                          r_confirm_date,
                          self.selfDic()['uid'],
                          self.selfDic()['time'],
                          r.id )
                self._cr.execute(sql)                
 
                        
    @api.multi                
    def selfDic(self):
        return {'uid':self._uid, 
                'date':fields.Date.context_today(self) ,
                'time': fields.Datetime.context_timestamp(self, timestamp=fields.datetime.now()),
                'com':self.env['res.company']._company_default_get().id }
        
    @api.model
    def check_selected_company_iscorrect(self):
        dates = self.env['wc.posting'].search([
            ('company_id','=', self.selfDic()['com']),('state','=','closed'),
        ], limit=1, order="name asc")
        if dates:
            raise ValidationError(_("Cannot continue the bulk approve for data migration.\n"\
                            "This company is regarded as daily operation already started.\n"\
                            "Please check the selected company is correct one, which you need to proceed bulk approve for data migration."))

                