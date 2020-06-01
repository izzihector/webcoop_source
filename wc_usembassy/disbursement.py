# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
import base64

from odoo.tools.misc import xlwt
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001


fmt_bold_left = xlwt.easyxf('font: bold on')
fmt_bold_right = xlwt.easyxf('font: bold on; align: horiz right')
fmt_bold_center = xlwt.easyxf('font: bold on; align: horiz center')

fmt_right = xlwt.easyxf('align: horiz right')
fmt_center = xlwt.easyxf('align: horiz center')

fmt_currency = xlwt.easyxf(num_format_str="#,##0.00")
fmt_currency_with_border = xlwt.easyxf(num_format_str="#,##0.00",strg_to_parse='align: horiz right;borders: left thin, right thin, top thin, bottom thin;')       

fmt_integer= xlwt.easyxf(num_format_str="#,##0")

fmt_bold_left_with_border = xlwt.easyxf('font: bold on;borders: left thin, right thin, top thin, bottom thin;')       
fmt_bold_right_with_border = xlwt.easyxf('font: bold on; align: horiz right;borders: left thin, right thin, top thin, bottom thin;')       
fmt_bold_center_with_border = xlwt.easyxf('font: bold on; align: horiz center;borders: left thin, right thin, top thin, bottom thin;')       

fmt_right_with_border = xlwt.easyxf('align: horiz right;borders: left thin, right thin, top thin, bottom thin;')       
fmt_center_with_border = xlwt.easyxf('align: horiz center;borders: left thin, right thin, top thin, bottom thin;')       

fmt_border = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin;')       
fmt_total =  xlwt.easyxf(num_format_str="#,##0.00",strg_to_parse='borders: top thin, bottom double;')

fmt_wrap = xlwt.easyxf('align: wrap on')
fmt_wrap_bold_border = xlwt.easyxf('font: bold on; align: horiz center,wrap on ; borders: left thin, right thin, top thin, bottom thin')



class Loan(models.Model):
    _inherit = "wc.loan"
    disbursement_id = fields.Many2one('wc.usemb.disbursement')
    fund_transfer_type = fields.Selection(related='member_id.fund_transfer_type')
    fund_transfer = fields.Char(related='member_id.fund_transfer')
    is_generated_disbursement = fields.Boolean()
    
    @api.onchange('disbursement_id')
    def onchange_disbursement_id(self):
        for l in self:
            if not l.disbursement_id:
                l.is_generated_disbursement = False
                

class Disbursement(models.Model):
    _name = "wc.usemb.disbursement"

    company_id = fields.Many2one('res.company', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan_disbursement'))
    bank = fields.Selection([('citi','CITI BANK'),('pnb','PNB BANK')],string="Bank")
    bank_person = fields.Char('To')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('gen', 'Generated'),
            ('canceled', 'Canceled')
        ], default="draft", track_visibility='onchange')


    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    date = fields.Date(default=get_first_open_date)
    bank_account_no =fields.Char('Bank Account No.')
    
    company_simple = fields.Char('Company')
    subject = fields.Char('Subject')
    wordings = fields.Text('Wordings')
    
    prepared_by = fields.Char('Prepared By')
    prepared_by_position= fields.Char('Position')
    reviewed_by = fields.Char('Reviewed By')
    reviewed_by_position= fields.Char('Position')
    approved_by1 = fields.Char('Approved By')
    approved_by1_position= fields.Char('Position')
    approved_by2 = fields.Char('Approved By')
    approved_by2_position= fields.Char('Position')
    
    loan_ids = fields.One2many('wc.loan','disbursement_id')
    total_amount = fields.Float('Total',compute='compute_amount')
    excel_data = fields.Binary('Excel File')
    
    @api.depends('loan_ids','loan_ids.is_generated_disbursement')
    def compute_amount(self):
        for d in self:
            total =0.0
            for l in d.loan_ids:
                if l.is_generated_disbursement:
                    total+=l.net_amount
            d.total_amount=total
    
    @api.onchange('bank')
    def onchange_bank(self):
        for s in self:
            if s.bank:
                for l in s.loan_ids:
                    if l.fund_transfer_type != s.bank:
                        s.loan_ids = False



    @api.onchange('bank_account_no','bank')
    def onchange_bank_account_id(self):
        for l in self:
            valu ={}
            if l.bank and l.bank_account_no:
                subj = "AITHORIZATION TO DEBIT %s NO. %s" % ("SA" if l.bank=='citi' else "CA",l.bank_account_no)
                valu['subject'] = subj
            return {'value':valu}
            
        return


    def search_target(self):
        self.ensure_one()
        ###get target loan data , and return
        loans = self.env['wc.loan'].search([
                    ('company_id','=',self.company_id.id),
                    '|',('disbursement_id','=',False),('disbursement_id','=',self.id),
                    ('state','in',['approved']),
                    ('member_id.fund_transfer_type','=',self.bank)
                    ])
        if loans:
            loans.write({'is_generated_disbursement':True})
            self.loan_ids = loans
        else:
            raise ValidationError(_("No data"))
        return 
    
    def back_to_draft(self):
        self.state = 'draft'
        return
    
    
    def cancel(self):
        self.ensure_one()
        self.state = 'canceled'
        self.write({'loan_ids': [(5,0,0)]})#remove all link
        return        
        
    @api.multi
    def write(self, values):
        values = self.remove_check_off(values)
        res = super(Disbursement, self).write(values)
        return res
    
    
    @api.constrains('loan_ids','loan_ids.fund_transfer_type','bank','excel_data')
    def validate_loan_ids(self):
        for s in self:
            for l in s.loan_ids:
                if l.fund_transfer_type != s.bank:
                    raise ValidationError(_("Fund Transfer and Bank is unmatch."))
                
            

    ##check if  loan_ids line was updated. If updated and the [is_generated_disbursement] is off, remover link from one2many
    ##capture ongoing update value when update disbursement record, and modify the update contents before update.
    def remove_check_off(self,values):
        if 'loan_ids' in values:##check if loan_ids line was updated
            for val in values['loan_ids']:
                if val[0] == 1 and 'is_generated_disbursement' in val[2]:##Check if [is_generated_disbursement] of the line as updated (val== [ 1 , id , { update contens}] in case of one2many field.)
                    if val[2]['is_generated_disbursement'] == False:
                        values['loan_ids'] += [[3,val[1]]]##add remove order by [3,id]. add the order in list of one2many values
                if val[0] == 2:
                    
                    val[0] = 3  #update flag 2 of one2many field means, delete record. But in this case, we need unlink loan onnly.So change flag 2 to 3.
        return values
            

    def gen_excel_file(self):
        if not self.loan_ids:
            raise ValidationError(_("No data.Please Search Target Loans first if not."))        
        if self.bank == 'citi':
            self.gen_excel_file_citi()
        elif self.bank == 'pnb':
            self.gen_excel_file_pnb()
            
        self.state = 'gen'
        return

            
#     def gen_excel_file_citi(self):
    def gen_excel_file_pnb(self):
       for d in self:
           wb = xlwt.Workbook()
           ws = wb.add_sheet(str(d.bank))

           ws.col(0).width = 256 * 5
           ws.col(1).width = 256 * 25
           ws.col(2).width = 256 * 35
           ws.col(3).width = 256 * 20
           ws.col(4).width = 256 * 10
           ws.col(5).width = 256 * 10
           ws.col(6).width = 256 * 10
               
               
           ws.write(1, 1, "To", fmt_bold_left)
           ws.write(1, 2, "", fmt_bold_left)
           ws.write(2, 2, "", fmt_bold_left)
           ws.write(4, 1, "FROM", fmt_bold_left)
           ws.write(4, 2, d.company_id.name or "", fmt_bold_left)
           ws.write(5, 2, "(%s)" % (d.company_simple if d.company_simple else "") , fmt_bold_left)
           ws.write(7, 1, "DATE", fmt_bold_left)
           ws.write(7, 2, d.date or "", fmt_bold_left)
           ws.write(9, 1, "SUBJECT", fmt_bold_left)
           ws.write(9, 2, d.subject or "", fmt_bold_left)

#           ws.write_merge(11, 13, 1, 4, d.wordings ,[fmt_bold_center_with_border ,frm_wrap])
           ws.write_merge(11, 13, 1, 4, d.wordings or "",fmt_wrap)

           ws.write(15, 1, "S.A. NUMBER", fmt_bold_center_with_border)
           ws.write(15, 2, "NAME", fmt_bold_center_with_border)
           ws.write(15, 3, "AMOUNT", fmt_bold_center_with_border)

           ri = 15
           ci = 1
           
           for loan in d.loan_ids:
               ri+=1
               ws.write(ri, 1, loan.member_id.fund_transfer or "",fmt_border)
               ws.write(ri, 2, loan.member_id.name or "",fmt_border)
               ws.write(ri, 3, loan.net_amount or 0,fmt_currency_with_border)
           
           ri+=2
           ws.write(ri, 3, d.total_amount or 0 ,fmt_total)

           ri+=4
           ws.write(ri, 1, 'PREPARED BY:')
           ws.write(ri, 3, 'REVIEWED BY:')

           ri+=3
           ws.write(ri, 1, d.prepared_by or "")
           ws.write(ri, 3, d.reviewed_by or "")
           ri+=1
           ws.write(ri, 1, d.prepared_by_position or "")
           ws.write(ri, 3, d.reviewed_by_position or "")

           ri+=2
           ws.write(ri, 1, 'APPROVED BY:')
           ws.write(ri, 3, 'APPROVED BY:')
           ri+=3
           ws.write(ri, 1, d.approved_by1 or "")
           ws.write(ri, 3, d.approved_by2 or "")
           ri+=1
           ws.write(ri, 1, d.approved_by1_position or "")
           ws.write(ri, 3, d.approved_by2_position or "")


           outputStream = StringIO()
           wb.save(outputStream)
           d.excel_data = base64.encodestring(outputStream.getvalue())
           outputStream.close()
       return           


#     def gen_excel_file_pnb(self):
    def gen_excel_file_citi(self):
    
       for d in self:
           wb = xlwt.Workbook()
           ws = wb.add_sheet(str(d.bank))

           ws.col(0).width = 256 * 5
           ws.col(1).width = 256 * 5
           ws.col(2).width = 256 * 15
           ws.col(3).width = 256 * 7
           ws.col(4).width = 256 * 7
           ws.col(5).width = 256 * 7
           ws.col(6).width = 256 * 7
           ws.col(7).width = 256 * 7
           ws.col(8).width = 256 * 15
           ws.col(9).width = 256 * 7
           ws.col(10).width = 256 * 7
           ws.col(11).width = 256 * 7
           ws.col(12).width = 256 * 25
           ws.col(13).width = 256 * 5

           ws.write(1, 2, "To", fmt_bold_left)
           ws.write(1, 3, "", fmt_bold_left)
           ws.write(2, 3, "", fmt_bold_left)
           ws.write(4, 2, "FROM", fmt_bold_left)
           ws.write(4, 3, d.company_id.name or "", fmt_bold_left)
           ws.write(5, 2, "(%s)" % (d.company_simple if d.company_simple else "") , fmt_bold_left)
           ws.write(7, 2, "DATE", fmt_bold_left)
           ws.write(7, 3, d.date or "", fmt_bold_left)
           ws.write(9, 2, "SUBJECT", fmt_bold_left)
           ws.write(9, 3, d.subject or "", fmt_bold_left)
           
#           ws.write_merge(11, 13, 2, 12, d.wordings , [fmt_bold_center_with_border ,frm_wrap])
           ws.write_merge(11, 13, 2, 12, d.wordings or "", fmt_wrap)


           ws.write(15, 1, "  ", fmt_center_with_border)
           ws.write(15, 2, "GL ACCT.NO", fmt_wrap_bold_border)
           ws.write(15, 3, "COST\nCTR", fmt_wrap_bold_border)
           ws.write(15, 4, "CURR\nCODE", fmt_wrap_bold_border)
           ws.write(15, 5, "CO.\nCODE", fmt_wrap_bold_border)
           ws.write(15, 6, "SER \nNO.", fmt_wrap_bold_border)
           ws.write(15, 7, "LCY\nAMT\n(DR)", fmt_wrap_bold_border)
           ws.write(15, 8, "LCY\nAMT\n(CR)", fmt_wrap_bold_border)
           ws.write(15, 9, "RATE", fmt_wrap_bold_border)
           ws.write(15, 10, "FCY\nAMT\n(DR)", fmt_wrap_bold_border)
           ws.write(15, 11, "FCY\nAMT\n(CR)", fmt_wrap_bold_border)
           ws.write(15, 12, "DESCRIPTION", fmt_wrap_bold_border)
           
           ws.row(15).height_mismatch = True
           ws.row(15).height = 256*3
           
#           ws.row(15).set_style(xlwt.easyxf('font:height 360;')) # 36pt
           


           ri = 15
           num = 0
           
           for loan in d.loan_ids:
               ri+=1
               num += 1
               ##fix 20200601
#               ws.write(ri, 1, ri ,fmt_center_with_border)
               ws.write(ri, 1, num ,fmt_center_with_border)
               ws.write(ri, 2, loan.member_id.fund_transfer or "",fmt_center_with_border)
               ws.write(ri, 3, "" ,fmt_border)
               ws.write(ri, 4, "" ,fmt_border)
               ws.write(ri, 5, "" ,fmt_border)
               ws.write(ri, 6, "" ,fmt_border)
               ws.write(ri, 7, "" ,fmt_border)
               ws.write(ri, 8, loan.net_amount or 0 ,fmt_currency_with_border)
               ws.write(ri, 9, "" ,fmt_border)
               ws.write(ri, 10, "" ,fmt_border)
               ws.write(ri, 11, "" ,fmt_border)
               ws.write(ri, 12, loan.member_id.name or "" ,fmt_border)
           
           ri+=2
           ws.write(ri, 8, d.total_amount or 0 ,fmt_total)
           
           ri+=2
           ws.write(ri, 1, 'PREPARED BY:')
           ws.write(ri, 6, 'REVIEWED BY:')
           
           ri+=2
           ws.write(ri, 1, d.prepared_by or "")
           ws.write(ri, 6, d.reviewed_by or "")
           ri+=1
           ws.write(ri, 1, d.prepared_by_position or "")
           ws.write(ri, 6, d.reviewed_by_position or "")

           ri+=2
           ws.write(ri, 1, 'APPROVED BY:')
           ws.write(ri, 6, 'APPROVED BY:')
           ri+=2
           ws.write(ri, 1, d.approved_by1 or "")
           ws.write(ri, 6, d.approved_by2 or "")
           ri+=1
           ws.write(ri, 1, d.approved_by1_position or "")
           ws.write(ri, 6, d.approved_by2_position or "")
           
           outputStream = StringIO()
           wb.save(outputStream)
           d.excel_data = base64.encodestring(outputStream.getvalue())
           outputStream.close()
       return
   
    @api.multi
    def download_as_excel(self):
        self.ensure_one()
        self.gen_excel_file()

        if not self.loan_ids:
            raise Warning(_("No distribution computed."))
        irconfig_obj = self.env['ir.config_parameter']
        base_url = irconfig_obj.get_param('report.url') or irconfig_obj.get_param('web.base.url')
        
        return {
            'type': 'ir.actions.act_url',
            'url':base_url + '/web/content/wc.usemb.disbursement/%s/excel_data/output.xls?download=true' % self.id,
#             'target':'self'
        }
       