# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
# from odoo.modules.module import get_module_resource
from datetime import datetime,date
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

#add for usembassy's special saving interest calculation style

class UsembSavingInterest(models.Model):
    _name = "wc.usemb.saving.interest.header"
    _description = "Saving Interest"
    _inherit = "mail.thread"

    def get_year(self):
        dt = fields.Date.from_string(fields.Date.context_today(self))
        dt -= relativedelta(years=1)
        return dt.strftime("%Y")

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.usemb.saving.interest.header'))

#     name = fields.Char("Year / Name",
#         readonly=True, states={'draft': [('readonly', False)]},
#         track_visibility='onchange',
#         default=get_year,
#         required=True)

    year = fields.Integer("Year",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        default=get_year,
        required=True)

    #set decimal digit 5 for divident percentage and patronage refund percentage
    rate = fields.Float("Rate %",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        digits=(12,5),
        required = True )
    
    account_type_id = fields.Many2one("wc.account.type"
                                      ,required=True
                                      ,domain=[('category','=','sa')])
#     date_from = fields.Date('Date From',required=True)
#     date_to = fields.Date('Date To',required=True)
    
    is_created_tran = fields.Boolean("")

    state = fields.Selection([
            ('draft', 'Draft'),
            ('calc', 'Calculated'),
            ('confirmed', 'Confirmed')
        ], 'State', default="draft",
        readonly=True, track_visibility='onchange')

    note = fields.Text('Notes', track_visibility='onchange')

    excel_data = fields.Binary('Excel File', compute='gen_excel_file')

    line_ids = fields.One2many('wc.usemb.saving.interest.detail', 'header_id',
        readonly=True, string='Lines')
    
    _sql_constraints = [('unique_code','unique(year,account_type_id,company_id)','Year field must be unique per account type')]


    def search_and_create_lines(self):
        self.line_ids.unlink()
        if self.year == False:
            raise ValidationError(_("Please set Year."))

        #get account which is not closed
        accounts = self.env['wc.account'].search([('company_id','=',self.company_id.id),
                                                  ('account_type_id','=',self.account_type_id.id),
                                                  ('state','!=','closed')])

        accounts.sorted(key=lambda x: x.member_id.id)

        #create every account's line
        for account in accounts:
            val = {'account_id':account.id,'member_id':account.member_id.id }
            self.line_ids = [(0,0,val)]
            
        self.state = "calc"

 
#Todo :excel file
    @api.multi
    @api.depends('year','account_type_id','line_ids','state')
    def gen_excel_file(self):
   
       fmt_bold_left = xlwt.easyxf('font: bold on')
       fmt_bold_right = xlwt.easyxf('font: bold on; align: horiz right')
       fmt_right = xlwt.easyxf('align: horiz right')
       fmt_currency = xlwt.easyxf(num_format_str="#,##0.00")
       fmt_integer= xlwt.easyxf(num_format_str="#,##0")
   
       for d in self:
           wb = xlwt.Workbook()
           ws = wb.add_sheet(str(d.year))

           ws.col(0).width = 256*20
           ws.col(1).width = 256*20
           for i in range(2, 5):
               ws.col(i).width = 256 * 10
           ws.col(6).width = 256*20
           ws.col(7).width = 256*20

           ri = 0
           ci = 0
           ws.write(ri, 0, "SAVING INTEREST COMPUTATION", fmt_bold_left)
#           ws.write(ri, 18, d.company_id.name, fmt_bold_left)
   
           ri += 1
           ws.write(ri, 0, "Year:", fmt_bold_left)
           ws.write(ri, 1, d.year)
           ri += 1
           ws.write(ri, 0, "Rate %:", fmt_bold_left)
           ws.write(ri, 1, d.rate, xlwt.easyxf(num_format_str="#,##0.00000"))
  
           headers = [
               ["Member", fmt_bold_left],
               ["Account", fmt_bold_left],
               ["Q1 Average",  fmt_bold_right],
               ["Q2 Average",  fmt_bold_right],
               ["Q3 Average",  fmt_bold_right],
               ["Q4 Average",  fmt_bold_right],
               ["Total",  fmt_bold_right],
               ["Int",  fmt_bold_right],
           ]
   
           ri += 3
           ci = 0
           for h in headers:
               ws.write(ri, ci, h[0], h[1])
               ci += 1
   
           for ln in d.line_ids:
               ri += 1
               ws.write(ri, 0, ln.member_id.name)
               ws.write(ri, 1, ln.account_id.name)
               ws.write(ri, 2, ln.q1_average,fmt_currency)
               ws.write(ri, 3, ln.q2_average,fmt_currency)
               ws.write(ri, 4, ln.q3_average,fmt_currency)
               ws.write(ri, 5, ln.q4_average,fmt_currency)
               ws.write(ri, 6, ln.q_average_total,fmt_currency)
               ws.write(ri, 7, ln.interest_amount,fmt_currency)
  
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
                     FROM wc_usemb_saving_interest_detail
                    where
                    header_id = %s and 
                    (COALESCE(q_average_total,0) = 0 and COALESCE(interest_amount,0) = 0 )
                """
                self._cr.execute(sql, (d.id,))
                
                self.invalidate_cache()
                
                        
                        
 
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
            'url':base_url + '/web/content/wc.usemb.saving.interest.header/%s/excel_data/output.xls?download=true' % self.id,
#             'target':'self'
        }
         
class DividendLines(models.Model):
    _name = "wc.usemb.saving.interest.detail"
    _description = "Saving Interest Details"
    _order = "name desc"

    header_id = fields.Many2one("wc.usemb.saving.interest.header",index=True, required=True, ondelete="cascade")
    name = fields.Char()
    #share_type = fields.Selection(related='dividend_id.share_type')
    member_id = fields.Many2one('wc.member', string='Member',
        domain=[('is_approved','=',True)],
        required=True)
    
    account_id = fields.Many2one('wc.account',
        required=True)
    q1_average = fields.Float("Q1 Average",compute="compute_q_average",store=True)
    q2_average = fields.Float("Q2 Average",compute="compute_q_average",store=True)
    q3_average = fields.Float("Q3 Average",compute="compute_q_average",store=True)
    q4_average = fields.Float("Q4 Average",compute="compute_q_average",store=True)
    q_average_total = fields.Float("Total Average",compute="compute_total_average",store=True)
    rate = fields.Float("wc.usemb.saving.interest.header",related="header_id.rate")
    interest_amount = fields.Float("Int amount",compute="compute_individual_int",store=True)
    member_code = fields.Char("Member ID", related="member_id.code")
#    membership_date = fields.Date("Membership Date", related="member_id.membership_date")

    @api.depends('account_id','header_id.year')
    def compute_q_average(self):
        for line in self:
            account_id = line.account_id
            year = line.header_id.year
            
            line.q1_average = line.get_q1_average(account_id,year)
            line.q2_average = line.get_q2_average(account_id,year)
            line.q3_average = line.get_q3_average(account_id,year)
            line.q4_average = line.get_q4_average(account_id,year)
        

    #function for special interest calculation style of usemb 
    def get_q_average(self,account_id,start_date=False):
        self.ensure_one()
        if not start_date:
            raise ValidationError(_("start date is no defined"))

        balance=[]
#         account_id = self.account_id.id

        balance_forward_date = start_date + relativedelta(days=-1)
        balance_forward = account_id.get_balance_at_date(account_id.id,balance_forward_date)
        balance.append(balance_forward)
        
        end_date = start_date + relativedelta(months=3)

        #other balance
        trans = self.env['wc.account.transaction'].search([
            ('company_id','=',self.header_id.company_id.id),
            ('account_id','=',account_id.id),
            ('state','=','confirmed'),
            ('date','>=',start_date),
            ('date','<',end_date),
            '|',
            ('deposit','>',0),('withdrawal','>',0),
            ])
        
        ####20200527
        balance_at_the_tran = balance_forward
        for tran in sorted(trans , key=lambda x:x.date):
            balance_at_the_tran += tran.deposit - tran.withdrawal
            balance.append(balance_at_the_tran)
        
#        for tran in trans:
#            balance_at_date = account_id.get_balance_at_date(account_id.id,tran.date)
#            balance.append(balance_at_date)
        
        if len(balance) > 0:
            average = sum(balance) / len(balance)

        return average
        
    def get_q1_average(self,account_id,year=False):
        if not year:
            raise ValidationError(_("year is no defined"))        
        start_date = datetime(year,1,1)
        return self.get_q_average(account_id,start_date)
        
    def get_q2_average(self,account_id,year=False):
        if not year:
            raise ValidationError(_("year is no defined"))        
        start_date = datetime(year,4,1)
        return self.get_q_average(account_id,start_date)

    def get_q3_average(self,account_id,year=False):
        if not year:
            raise ValidationError(_("year is no defined"))        
        start_date = datetime(year,7,1)
        return self.get_q_average(account_id,start_date)
    
    def get_q4_average(self,account_id,year=False):
        if not year:
            raise ValidationError(_("year is no defined"))        
        start_date = datetime(year,10,1)
        return self.get_q_average(account_id,start_date)
        

    @api.depends('q1_average','q2_average','q3_average','q4_average')
    def compute_total_average(self):
        for line in self:
            line.q_average_total = line.q1_average + line.q2_average + line.q3_average + line.q4_average

    
    @api.depends('q_average_total','rate')
    def compute_individual_int(self):
        for line in self:
            line.interest_amount = line.q_average_total * line.rate / 100
            
