from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import time

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Posting(models.Model):
    _inherit = "wc.posting"

    #over write close_date operation for fixing f540 issues
    #this was kind of bug , so overwrite the method by the method below.
    #the source code was copied , and modified part of it.
    @api.multi
    def close_date(self):
        start = time.time()
        _logger.debug("***#close_date: start")

        first = True
        for rec in self:
            rec.add_details()
            rec.state = 'closed'

            if first:
                first = False

                #delete all draft transactions
                #account transactions
                trans = self.env['wc.account.transaction'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT trans: %s", trans)
                if trans:
                    #f540 fix
                    #trans.unlink()
                    raise ValidationError(_("Draft record is remaining in %s! Please confirm or delete it before closing.") % ('account transactions '))


                coll_lines = self.env['wc.collection.line'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT coll lines: %s", coll_lines)
                if coll_lines:
                    #f540 fix
                    #coll_lines.unlink()
                    raise ValidationError(_("Draft record is remaining in %s! Please confirm or delete it before closing.") % ('collection line '))

                collection = self.env['wc.collection'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT collection: %s", collection)
                if collection:
                    #f540 fix
                    #for coll in collection:
                    #    coll.loan_id = False
                    #    coll.loan_payment_id = False
                    #collection.unlink()
                    raise ValidationError(_("Draft record is remaining in %s! Please confirm or delete it before closing.") % ('collection '))

                pay = self.env['wc.loan.payment'].sudo().search([
                    ('state','=','draft'),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                _logger.debug("*DRAFT loan payment: %s", pay)
                if pay:
                    #f540 fix
                    #for p in pay:
                    #    p.collection_id = False
                    #pay.unlink()
                    raise ValidationError(_("Draft record is remaining in %s! Please confirm or delete it before closing.") % ('payment transactions '))

        _logger.debug("***#close_date: stop elapsed=%s", time.time() - start)

