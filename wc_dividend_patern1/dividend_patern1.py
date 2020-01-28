# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime,date
from dateutil.relativedelta import relativedelta

from odoo.tools.misc import xlwt
import logging
import time
import base64
from lib2to3.pgen2.token import ISEOF
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#f605 add start
class Loan(models.Model):
    _inherit = "wc.loan"
    
    interest_total_usemb = fields.Float("Total Interest", digits=(12,2),
        compute="_compute_total_interest_usemb")
    
    @api.depends('details.interest_paid',
                 'deduction_ids',
                 'deduction_ids.amount',
                 'deduction_ids.code')
    def _compute_total_interest_usemb(self):
        for loan in self:
            amt=0.0
            if len(loan.details) > 0:
                amt = sum(a.interest_paid for a in loan.details)
    
            check_module = self.env['ir.module.module'].search([('name', '=', 'wc_usembassy')])
            for ded in loan.deduction_ids:
                if ded.code == "ADV-INT" or ded.code.upper()[:3] == 'ADV':
                    amt += ded.amount 
                if check_module and check_module.state == "installed":
                    if ded.code == "BASE-INT":
                        amt += ded.amount
            
            loan.interest_total_usemb = amt
#f605 add end

class Account(models.Model):
    _inherit = "wc.account"
    
    def get_acc_balance_at_date(self,date):
        #refer saving interest calculation
        amt = 0
        if date == False:
            amt = sum(tran.deposit - tran.withdrawal for tran in self.transaction_ids)
        else:
            amt = sum(tran.deposit - tran.withdrawal for tran in self.transaction_ids if datetime.strptime(tran.date,DF).date() <= date)
        return amt
            

    #get date parameter for cbu balance.For examplt, if it is 7th ,balance at Jan 7th is regarded as Jan's balance
    def get_date_for_monthly_balance(self):
        company_id = self.env.user.company_id
        return company_id.date_parameter_for_cbu_balance or self.env.ref('base.main_company').date_parameter_for_cbu_balance

    #return monthly cbu balance , and total , and average 
    def get_monthly_balance(self,year):
        month_bal = []
        is_existing = False
        #if no data , regard as 31. means , end of the month balance is regarded as the month's balance
        date = self.get_date_for_monthly_balance() or 31
        for i in range(1,13):
            t_date = date(year,i,1) + relativedelta(day=date)
            bal = self.get_acc_balance_at_date(t_date)
            month_bal.append(bal)
            if not is_existing and bal > 0 :
                is_existing = True
        return month_bal , is_existing

class Member(models.Model):
    _inherit = "wc.member"


    #get and return debit and credit amount total for all loan interest account
    def get_loan_int_summary_4member(self, date_from=False, date_to=False):
        partner_id = self.partner_id.id
        return self.env['account.move.line'].get_total_loan_interest_amount(date_from, date_to, partner_id)
 
    def get_monthly_balance_per_member(self,year):
        month_bal = []
        is_existing = False
        #if no data , regard as 31. means , end of the month balance is regarded as the month's balance
        date_for_div = self.env['wc.account'].get_date_for_monthly_balance() or 31
        for i in range(1,13):
            t_date = date(int(year),i,1) + relativedelta(day=date_for_div)
            bal = 0
            for acc in self.cbu_account_ids:
                bal += acc.get_acc_balance_at_date(t_date)
            month_bal.append(bal)
            if not is_existing and bal > 0 :
                is_existing = True
        return month_bal , is_existing
    
    def get_monthly_balance_per_member_by_fromTo(self,date_from,date_to):
        month_bal = []
        is_existing = False
        #if no data , regard as 31. means , end of the month balance is regarded as the month's balance
        date_for_div = self.env['wc.account'].get_date_for_monthly_balance() or 31

        date_from_dt = datetime.strptime(date_from,DF).date()
        date_to_dt = datetime.strptime(date_to,DF).date()       
        if date_from_dt.year != date_to_dt.year:
            raise ValidationError(_("Cannot use the term over the year-end."))
        
        year = date_from_dt.year
        for i in range(1,13):
            t_date = date(int(year),i,1) + relativedelta(day=date_for_div-1)
            if date_from_dt <= t_date and t_date <= date_to_dt:
                bal = 0
                for acc in self.cbu_account_ids:
                    bal += acc.get_acc_balance_at_date(t_date)
                month_bal.append(bal)
                if not is_existing and bal > 0 :
                    is_existing = True
            else:
                month_bal.append(0)
                    
        return month_bal , is_existing

    

    #return monthly cbu balance , and total , and average 
    def get_monthly_balance(self,year):
        month_bal = []
        is_existing = False
        #if no data , regard as 31. means , end of the month balance is regarded as the month's balance
        date = self.get_date_for_monthly_balance() or 31
        for i in range(1,13):
            t_date = date(year,i,1) + relativedelta(day=date)
            bal = self.get_acc_balance_at_date(t_date)
            month_bal.append(bal)
            if not is_existing and bal > 0 :
                is_existing = True
        return month_bal , is_existing
 
#     @api.model
#     def get_interest_income_account_id(self):
#         res = super(Loan, self).get_interest_income_account_id() \
#             or self.env.user.company_id.interest_income_account_id.id
#         if not res:
#             raise Warning(_("Interest income GL account is not set in Companies/Branch/Account Settings or Loan Type."))
#         return res


    #f605 add get interest amount during certain period of loan    
    #MEMO 20200107
    #actually ,transaction date of interest income is depending on payment date of each amortization schedule
    # But in this module , we regard transaction date of interest income is same as loan approve date 
    # because in usemb case, every interest amount is deducted at the begining of loan(upfront interest).
    def get_loan_int_summary_4member_usemb(self, date_from=False, date_to=False):
        self.ensure_one()
        member = self
        int_total = 0.00
        loans = self.env['wc.loan'].search([('member_id','=',member.id),
                                            ('date','>=',date_from),
                                            ('date','<=',date_to),
                                            ('state','!=','draft')])
        for loan in loans:
            int_total += loan.interest_total_usemb
        
        return int_total




class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    def get_total_loan_interest_accounts(self):
        all_int_accounts = []
        all_loan_types = self.env['wc.loan.type'].search([('company_id','=',self.company_id.id)])
        for loan_type in all_loan_types:
            if loan_type.interest_income_account_id.id not in all_int_accounts:
                all_int_accounts.append(loan_type.interest_income_account_id.id)
            
        default_acc = self.env.user.company_id.interest_income_account_id.id
        if default_acc not in all_int_accounts:
            all_int_accounts.append(default_acc)
        return all_int_accounts
    
    def get_total_loan_interest_amount(self,date_from=False, date_to=False , partner_id=False):
        all_int_accounts = self.get_total_loan_interest_accounts()        
        return self.get_acc_summary_4account_4partner(date_from, date_to,all_int_accounts,partner_id)
        
    def get_acc_summary_4account_4partner(self, 
                                          date_from=False,
                                          date_to=False,
                                          gl_account_ids=[],
                                          partner_id=False):
        if len(gl_account_ids) == 0:
            raise ValidationError(_("loan interest account is not set."))
        domain = [('account_id','in',gl_account_ids)]

        if partner_id:
            domain.append(('partner_id','=',partner_id))
        if date_from:
            domain.append(('date','>=',date_from))
        if date_to:
            domain.append(('date','<=',date_to))        
        trans = self.env['account.move.line'].search(domain)
        debit ,credit = 0,0
        debit ,credit = sum(r.debit for r in trans), sum(r.credit for r in trans)        
        return debit , credit


class Dividend(models.Model):
    _name = "wc.dividend.patern1"
    _description = "Dividend Distribution"
    _inherit = "mail.thread"

    def get_year(self):
        dt = fields.Date.from_string(fields.Date.context_today(self))
        dt -= relativedelta(years=1)
        return dt.strftime("%Y")

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.dividend.patern1'))

    name = fields.Char("Year / Name",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        default=get_year,
        required=True)
    
    total_amt_for_dividend = fields.Float('Total Available Amount for Dividend Distribution')
    total_amt_for_patronage = fields.Float('Total Available Amount for Patronage Refund')
    
    total_average_share = fields.Float('TASM')
    total_int_on_loan = fields.Float('Total Loan Interest Income')

    #set decimal digit 5 for divident percentage and patronage refund percentage
    dividend_pct = fields.Float("Dividend %",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        digits=(12,5))

    #set decimal digit 5 for divident percentage and patronage refund percentage
    patronage_pct = fields.Float("Patronage %",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        digits=(12,5))

    state = fields.Selection([
            ('draft', 'Draft'),
            ('calc', 'Calculated'),
            ('confirmed', 'Confirmed')
        ], 'State', default="draft",
        readonly=True, track_visibility='onchange')

    note = fields.Text('Notes', track_visibility='onchange')

    excel_data = fields.Binary('Excel File', compute='gen_excel_file')

    line_ids = fields.One2many('wc.dividend.patern1.line', 'dividend_id',
        readonly=True, string='Lines')
    
    date_from = fields.Date('Date From',required=True)
    date_to = fields.Date('Date To',required=True)
    
    is_calculate_dividend = fields.Boolean('For Dividend',help="check on if you calculat dividend")
    is_calculate_patronage_refund = fields.Boolean('For Patronage Refund',help="check on if you calculat dividend")
    
    _sql_constraints = [('unique_code','unique(name,company_id)','Name field must be unique per branch')]

    def search_and_create_patronage_refund_line(self,date_from_dt,date_to_dt):

        #1.get total interest income amount from each member      
        for line in self.line_ids:
            
            member = line.member_id
            _logger.debug("**create patronage line start** %s" % (member.code))
            #f605 mod start
#             debit, credit = member.get_loan_int_summary_4member(date_from_dt,date_to_dt)
#             each_int = credit - debit
            each_int = member.get_loan_int_summary_4member_usemb(date_from_dt,date_to_dt)            
            #f605 mod end

            line.write({'loan_interest_income' :each_int })
            _logger.debug("**create patronage line end** %s" % (member.code))
            

        #2 get total and calculate rate
        self.total_int_on_loan = sum(line.loan_interest_income for line in self.line_ids)
        if self.total_int_on_loan == False or self.total_int_on_loan <= 0:
            raise ValidationError(_("No interest amount Or summary is less than 0"))
        
        r2 = round(self.total_amt_for_patronage / self.total_int_on_loan , 7)
        self.patronage_pct = r2 * 100
        #3.set individual refund amount
            #auto calculate

    def search_and_create_dividend_line(self,date_from_dt,date_to_dt):
        #1.get each month cbu balance 
        for line in self.line_ids:

            
            member = line.member_id
            month_bal , is_existing = member.get_monthly_balance_per_member_by_fromTo(date_from_dt,date_to_dt)
            _logger.debug("**create dividend line start** %s" % (member.code))
            
#             month_bal , is_existing = member.get_monthly_balance_per_member(year)
            val = {}
            for i in range(1,13):
                val['cbu_amount_' + str(i)] = month_bal[i-1]
            line.write(val)
            _logger.debug("**create dividend line end**")
            
            
        #2.get [ASM] (total share month)  
               #> auto calculate when updating line data
            
        #3.get [TASM] (total average share month) 
        self.total_average_share = sum(rec.cbu_amount_calc_average for rec in self.line_ids)
            
        if self.total_average_share == False or self.total_average_share <= 0:
            raise ValidationError(_("CBU balance is less than 0"))
        
        #4.get [R1] (interest rate on share capital)
        #get upto 7th decimal digit
        r1 = round(self.total_amt_for_dividend / self.total_average_share, 7)
        self.dividend_pct = r1 * 100
    
        #5.calculate each [IISC] (Individual interest on share capital)
            #auto calculate        

    def search_and_create_lines(self):
        self.line_ids.unlink()
        if self.date_from == False or self.date_to == False:
            raise ValidationError(_("Please set Date From and Date To."))
        
        date_from_dt = datetime.strptime(self.date_from,DF).date()
        date_to_dt = datetime.strptime(self.date_to,DF).date()
        if date_from_dt.year != date_to_dt.year:
            raise ValidationError(_("Cannot use the term over the year-end."))

#         year = self.name
        members = self.env['wc.member'].search([('company_id','=',self.company_id.id)])
        

        #create every member's line
        for member in members:
            _logger.debug("**create member line start** %s" % member.id)

            val = {'member_id':member.id ,'dividend_id':self.id}
#improve performance 20191203
            self.env['wc.dividend.patern1.line'].create(val)
#             self.line_ids = [(0,0,val)]
            _logger.debug("**create member line end** %s" % member.id)


        #dividend
        if self.is_calculate_dividend:
            self.search_and_create_dividend_line(self.date_from,self.date_to)

        #patronage
        if self.is_calculate_patronage_refund:
            self.search_and_create_patronage_refund_line(self.date_from,self.date_to)
                    
        self.state = "calc"


#Todo :excel file
    @api.multi
    @api.depends('name','line_ids','state')
    def gen_excel_file(self):
  
       fmt_bold_left = xlwt.easyxf('font: bold on')
       fmt_bold_right = xlwt.easyxf('font: bold on; align: horiz right')
       fmt_right = xlwt.easyxf('align: horiz right')
       fmt_currency = xlwt.easyxf(num_format_str="#,##0.00")
       fmt_integer= xlwt.easyxf(num_format_str="#,##0")
  
       for d in self:
           wb = xlwt.Workbook()
           ws = wb.add_sheet(d.name)
  
           ws.col(0).width = 256*20
           for i in range(1, 13):
               ws.col(i).width = 256 * 7
           for i in range(13, 19):
               ws.col(i).width = 256 * 10
  
           ri = 0
           ci = 0
           ws.write(ri, 0, "DIVIDEND AND PATRONAGE COMPUTATION", fmt_bold_left)
           ws.write(ri, 18, d.company_id.name, fmt_bold_left)
  
           ri += 1
           ws.write(ri, 0, "Year:", fmt_bold_left)
           ws.write(ri, 4, d.name)
           ri += 1
           ws.write(ri, 0, "Total Amount for Dividend Distribution:", fmt_bold_left)
           ws.write(ri, 4, d.total_amt_for_dividend)
           ri += 1
           ws.write(ri, 0, "Total Amount for Patronage Refund:", fmt_bold_left)
           ws.write(ri, 4, d.total_amt_for_patronage)
           ri -= 1
           ws.write(ri, 8, "TASM:", fmt_bold_left)
           ws.write(ri, 10, d.total_average_share, xlwt.easyxf(num_format_str="#,##0.00"))
           ws.write(ri, 13, "Dividend %:", fmt_bold_left)
           ws.write(ri, 15, d.dividend_pct, xlwt.easyxf(num_format_str="#,##0.00000"))
           ri += 1
           ws.write(ri, 8, "Total Loan Int:", fmt_bold_left)
           ws.write(ri, 10, d.total_int_on_loan, xlwt.easyxf(num_format_str="#,##0.00"))
           ws.write(ri, 13, "Patronage %:", fmt_bold_left)
           ws.write(ri, 15, d.patronage_pct, xlwt.easyxf(num_format_str="#,##0.00000"))
 
           headers = [
               ["Member", fmt_bold_left],
               ["JAN",  fmt_bold_right],
               ["FEC",  fmt_bold_right],
               ["MAR",  fmt_bold_right],
               ["APR",  fmt_bold_right],
               ["MAY",  fmt_bold_right],
               ["JUN",  fmt_bold_right],
               ["JUL",  fmt_bold_right],
               ["AUG",  fmt_bold_right],
               ["SEP",  fmt_bold_right],
               ["OCT",  fmt_bold_right],
               ["NOV",  fmt_bold_right],
               ["DEC",  fmt_bold_right],
               ["TSM",  fmt_bold_right],
               ["ASM",  fmt_bold_right],
               ["Dividend",  fmt_bold_right],
               ["Loan Int",  fmt_bold_right],
               ["Patronage", fmt_bold_right],
               ["Total",     fmt_bold_right],
           ]
  
           ri += 2
           ci = 0
           for h in headers:
               ws.write(ri, ci, h[0], h[1])
               ci += 1
  
           for ln in d.line_ids:
               ri += 1
               ws.write(ri, 0, ln.member_id.name)
               for j in range(1,13):
                   ws.write(ri, j, ln['cbu_amount_' + str(j)])
               ws.write(ri, 13, ln.cbu_amount_calc_total)
               ws.write(ri, 14, ln.cbu_amount_calc_average)
               ws.write(ri, 15, ln.dividend_on_cbu)
               ws.write(ri, 16, ln.loan_interest_income)
               ws.write(ri, 17, ln.patronage_refund)
               ws.write(ri, 18, ln.total_dividend_and_refund)
 
           outputStream = StringIO()
           wb.save(outputStream)
           d.excel_data = base64.encodestring(outputStream.getvalue())
           outputStream.close()
       return           

    @api.multi
    def confirm(self):
        for d in self:
            if d.state=='calc':
#                 d.search_and_create_divident_line()
                d.state = 'confirmed'
                sql = """
                    delete 
                     FROM wc_dividend_patern1_line
                    where
                    dividend_id = %s and 
                    COALESCE(loan_interest_income,0)
                    +COALESCE(cbu_amount_1,0)
                    +COALESCE(cbu_amount_2,0)
                    +COALESCE(cbu_amount_3,0)
                    +COALESCE(cbu_amount_4,0)
                    +COALESCE(cbu_amount_5,0)
                    +COALESCE(cbu_amount_6,0)
                    +COALESCE(cbu_amount_7,0)
                    +COALESCE(cbu_amount_8,0)
                    +COALESCE(cbu_amount_9,0)
                    +COALESCE(cbu_amount_10,0)
                    +COALESCE(cbu_amount_11,0)
                    +COALESCE(cbu_amount_12,0)
                    =0
                """
                self._cr.execute(sql, (d.id,))

                
                self.env['wc.dividend.patern1.line'].invalidate_cache()
#                 rec = self.env['wc.dividend.patern1.line'].search(
#                     [('dividend_id','=',self.id),
#                      '|',('loan_interest_income','=',0),('loan_interest_income','=',False),
#                      '|',()
#                      ]
#                     )
#                 rec.unlink()
# #                 for line in d.line_ids:
#                     if line.total_dividend_and_refund == False or line.total_dividend_and_refund == 0:
#                         line.unlink()





    @api.multi
    def back_to_draft(self):
        for d in self:
            if d.state!='draft':
                d.state = 'draft'
                d.line_ids.unlink()


    @api.multi
    def download_as_excel(self):
        self.ensure_one()
        if not self.line_ids:
            raise Warning(_("No distribution computed."))
#         return {
#             'type': 'ir.actions.report.xml',
#             'report_type': 'controller',
#             'report_file': '/web/content/wc.dividend.patern1/%s/excel_data/output.xls?download=true' % self.id,
#         }
        irconfig_obj = self.env['ir.config_parameter']
        base_url = irconfig_obj.get_param('report.url') or irconfig_obj.get_param('web.base.url')
        return {
            'type': 'ir.actions.act_url',
            'url':base_url + '/web/content/wc.dividend.patern1/%s/excel_data/output.xls?download=true' % self.id,
#             'target':'self'
        }
         
        
        
        
class DividendLines(models.Model):
    _name = "wc.dividend.patern1.line"
    _description = "Dividend Calculation"
    _order = "name desc"

    dividend_id = fields.Many2one('wc.dividend.patern1', string='Dividend Distribution',
        index=True, required=True, ondelete="cascade")

    name = fields.Char()
    #share_type = fields.Selection(related='dividend_id.share_type')

    member_id = fields.Many2one('wc.member', string='Member',
        domain=[('is_approved','=',True)],
        required=True)

    member_code = fields.Char("Member ID", related="member_id.code")
#    membership_date = fields.Date("Membership Date", related="member_id.membership_date")

    cbu_amount_1 = fields.Float(digits=(12,2))
    cbu_amount_2 = fields.Float(digits=(12,2))
    cbu_amount_3 = fields.Float(digits=(12,2))
    cbu_amount_4 = fields.Float(digits=(12,2))
    cbu_amount_5 = fields.Float(digits=(12,2))
    cbu_amount_6 = fields.Float(digits=(12,2))
    cbu_amount_7 = fields.Float(digits=(12,2))
    cbu_amount_8 = fields.Float(digits=(12,2))
    cbu_amount_9 = fields.Float(digits=(12,2))
    cbu_amount_10 = fields.Float(digits=(12,2))
    cbu_amount_11 = fields.Float(digits=(12,2))
    cbu_amount_12 = fields.Float(digits=(12,2))    
    cbu_amount_calc_total = fields.Float(digits=(12,2),compute="compute_cbu_average")
    cbu_amount_calc_average = fields.Float(digits=(12,2),compute="compute_cbu_average")
    
    dividend_on_cbu = fields.Float(digits=(12,2),compute="compute_individual_dividend")
    loan_interest_income = fields.Float(digits=(12,2))
    patronage_refund = fields.Float(digits=(12,2),compute="compute_individual_refund")
    
    total_dividend_and_refund = fields.Float(digits=(12,2),compute="compute_individual_total")
    
    is_calculate_dividend = fields.Boolean(related='dividend_id.is_calculate_dividend')
    
    @api.depends('dividend_id.dividend_pct')
    def compute_individual_dividend(self):
        for line in self:
            pct = line.dividend_id.dividend_pct
            if pct > 0:
                line.dividend_on_cbu = line.cbu_amount_calc_average * pct / 100

    @api.depends('dividend_id.patronage_pct')
    def compute_individual_refund(self):
        for line in self:
            pct = line.dividend_id.patronage_pct
            if pct > 0:
                line.patronage_refund = line.loan_interest_income * pct / 100

    @api.depends('dividend_on_cbu','patronage_refund')
    def compute_individual_total(self):
        for line in self:
            line.total_dividend_and_refund = line.dividend_on_cbu + line.patronage_refund

        
    
    @api.depends('cbu_amount_1','cbu_amount_2','cbu_amount_3','cbu_amount_4','cbu_amount_5',
                 'cbu_amount_6','cbu_amount_7','cbu_amount_8','cbu_amount_9',
                 'cbu_amount_10','cbu_amount_11','cbu_amount_12')
    def compute_cbu_average(self):
        for line in self:
            total = line.cbu_amount_1 + \
                line.cbu_amount_2 + \
                line.cbu_amount_3 + \
                line.cbu_amount_4 + \
                line.cbu_amount_5 + \
                line.cbu_amount_6 + \
                line.cbu_amount_7 + \
                line.cbu_amount_8 + \
                line.cbu_amount_9 + \
                line.cbu_amount_10 + \
                line.cbu_amount_11 + \
                line.cbu_amount_12
            
            line.cbu_amount_calc_total = total
            line.cbu_amount_calc_average = round(total / 12,2)

