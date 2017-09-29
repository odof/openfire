# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, models


class OFCRMActivityLog(models.TransientModel):
    _inherit = "crm.activity.log"

    @api.multi
    def action_log(self):
        crm_suivi = self.env.user.company_id.crm_suivi
        crm_suivi_notes = self.env.user.company_id.crm_suivi_notes
        if crm_suivi:
            for log in self:
                new_line = "<p>%(date)s%(user)s%(type)s%(title)s%(note)s</p>" % {
                    'date': datetime.now().date().strftime('%d/%m/%y'),
                    'user': " - %s" % self.env.user.name,
                    'type': log.next_activity_id and " - %s" % log.next_activity_id.name or "",
                    'title': log.title_action and " - %s" % log.title_action or "",
                    'note': crm_suivi_notes and log.note and "<br/><em>%s</em>" % log.note.replace("<p>", "<span style='padding-left: 16px;'>").replace("</p>","</span><br/>").replace("<br></span><br/>","</span><br/>") or "",
                }
                suivi = log.lead_id.description
                suivi = new_line + suivi
                log.lead_id.write({'description': suivi})
        return super(OFCRMActivityLog, self).action_log()
