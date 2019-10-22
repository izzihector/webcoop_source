# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class LoanPayments(models.Model):

    _inherit = 'wc.loan.payment'

#overwrite for b580
    @api.model
    def post_payment_per_soa_line(self, p):
        _logger.debug("Post Payment: pstate=%s lstate=%s", p.state, p.loan_id.state)

        if p.state=='draft' and p.loan_id.state in ['approved','past-due'] :

            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',p.loan_id.id),
                ('total_due','>',0.0),
                ('state','!=','del'),
            ], order='date_due')
            if not details:
                #b580
                raise UserError(_("Target SOA line for this payment doesn't exist."))                        
                return

            dist_lines = []
            pamt = p.amount - p.posted_amount

            #penalty
            if p.loan_id.is_collect_penalty:
                lines, pamt = self.get_penalty_lines(p, details, pamt)
                dist_lines += lines

            #interest due
            lines, pamt = self.get_interest_lines(p, details, pamt)
            dist_lines += lines

            #others due
            lines, pamt, dtrans_lines = self.get_other_lines(p, details, pamt)
            dist_lines += lines

            #principal due
            pcp_lines, pamt = self.get_principal_lines(p, details, pamt)
            dist_lines += pcp_lines

            #create trans
            self.post_create_trans(p, dist_lines, pcp_lines, dtrans_lines, pamt)




#

