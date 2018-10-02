from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging, time
_logger = logging.getLogger(__name__)
DF = '%Y-%m-%d'


class ReportWizard(models.TransientModel):
    _name = 'wc.account.report.wizard'
    _description = 'Account Transaction Summary Report Wizard'

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.account.type'))

    #search condition
    date1 = fields.Date('Date From', default=fields.Date.context_today, required=True)
    date2 = fields.Date('Date To', default=fields.Date.context_today ,required=True)
    account_type_id = fields.Many2one('wc.account.type', string='Account Type',required=True)
    trcode_id = fields.Many2one('wc.tr.code', string='Transaction Code')
    teller_id = fields.Many2one('res.users', string='Teller')

    #invisible field
    trans_type = fields.Char(compute='compute_trans_type')

    @api.multi
    def account_tran_report(self):
        self.ensure_one()
        data = {}
        whrlist =[
            ('date', '>=', self.date1),
            ('date', '<=', self.date2),
            ('account_type_id', '=', self.account_type_id.id),
            ('state','in',['clearing','confirmed']),
        ]
        if self.trcode_id:
           whrlist.append(('trcode_id', '=', self.trcode_id.id))
        if self.teller_id:
           whrlist.append(('teller_id', '=', self.teller_id.id))

        res = self.env['wc.account.transaction'].search(whrlist)

        data['doc_ids'] = res.ids
        data['form'] = self.read(['date1', 'date2','account_type_id','trcode_id','teller_id'])[0]

        _logger.debug('print_report: filter=%s data=%s', whrlist, data)
        return self.env['report'].with_context(landscape=True).get_action(self, 'wc_account.account_tran_report', data=data)

    @api.multi
    @api.depends('account_type_id')
    def compute_trans_type(self):
        for r in self:
            r.trans_type = r.account_type_id.category == 'cbu' and 'cbu' or 'sa'

    @api.onchange('account_type_id')
    def oc_account_id(self):
        self.ensure_one()
        if self.trans_type == 'cbu':
            domain = {'trcode_id': [('trans_type', '=', 'cbu')]}
        else:
            domain = {'trcode_id': [('trans_type', '!=', 'cbu')]}
        _logger.info('***Change trcode domain: %s', domain)
        return {'domain': domain}


class AccountTransaction(models.AbstractModel):
    _name = 'report.wc_account.account_tran_report'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_account.account_tran_report')
        if not docids:
            ids = data['doc_ids']
        else:
            ids = docids
        _logger.debug('account_tran_report: data=%s', data)
        if not data:
            date1 = fields.Date.from_string(fields.Date.context_today(self))
            date2 = fields.Date.from_string(fields.Date.context_today(self))
        else:

            date1 = fields.Date.from_string(data['form']['date1'])
            date2 = fields.Date.from_string(data['form']['date2'])

        docs = self.env['wc.account.transaction'].browse(ids)

        docargs = {'doc_ids': ids,
           'doc_model': self.env['wc.account.transaction'],
           'docs' : docs.sorted(key=lambda r: '%s-%s' % (r.date, r.account_id.member_code)),
           'time': time,
           'data': data,
           'date1': date1 and date1.strftime('%B %d, %Y'),
           'date2': date2 and date2.strftime('%B %d, %Y'),
           'account_type' : data['form']['account_type_id'][1],
           'trcode' : data['form']['trcode_id'][1] if data['form']['trcode_id'] else False,
           'teller' : data['form']['teller_id'][1] if data['form']['teller_id'] else False
           }
        _logger.debug('account_tran_report: args=%s', docargs)
        return report_obj.render('wc_account.account_tran_report', docargs)
