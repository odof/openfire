# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, models


class OFCRMActivityLog(models.TransientModel):
    _inherit = "crm.activity.log"

    @api.multi
    def action_log(self):
        for log in self:
            new_line = "<p>%(date)s%(title)s</p>" % {
                'date': datetime.now().date().strftime('%d/%m/%y'),
                'title': log.title_action and " - %s" % log.title_action or "",
                #'note': log.note and " - %s" % log.note or "",
            }
            suivi = log.lead_id.description
            suivi = new_line + suivi
            log.lead_id.write({'description': suivi})
        return super(OFCRMActivityLog, self).action_log()
