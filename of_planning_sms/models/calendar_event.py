# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


class OFPlanningIntervention(models.Model):
    _inherit = 'calendar.event'

    of_is_customer_sms_sent = fields.Boolean(string="Customer SMS sent ?", default=False)

    def action_send_sms(self):
        return self.env['of.sms'].action_send_sms(self.id, 'calendar.event', self.of_partner_id)

    # Appelé par cron journalier de rappel d'intervention
    @api.model
    def cron_sms_notif_daily(self):
        # On récupère la date de demain (fuseau Europe/Paris) sous forme de chaîne.
        # Si on est samedi, il faut envoyer les textos de rappel du lundi,
        #   donc dans ce cas le lendemain, c'est dans 2 jours !
        now = fields.datetime.now()
        tomorrow_date = (fields.Datetime.context_timestamp(self, now) + timedelta(days=1)).strftime(
            DEFAULT_SERVER_DATE_FORMAT
        )
        if now.isoweekday() == 6:  # 6 est le samedi.
            end_date_reminder_str = (fields.Datetime.context_timestamp(self, now) + timedelta(days=2)).strftime(
                DEFAULT_SERVER_DATE_FORMAT
            )
        elif now.isoweekday() == 7:  # 7 est le dimanche. On n'envoie pas de texto le dimanche.
            return True
        else:
            end_date_reminder_str = tomorrow_date

        intervention_obj = self.env["calendar.event"]

        # On récupère l'émetteur du texto
        model = self.env['ir.model'].search([('model', '=', 'calendar.event')], limit=1)
        if model:
            sender = self.env['of.sms.sender'].search([('model', '=', model)], limit=1)
        else:
            sender = self.env['of.sms.sender'].search([('model', '=', '')], limit=1)

        if not sender:
            _logger.error("This customer has no valid mobile number!")
            return False

        # On récupère le pays "France" comme pays par défaut pour le code téléphonique (+33...) des destinataires
        #   dont le pays ne serait pas configuré.
        country_id_defaut = self.env["res.country"].search([('code', '=', 'FR')])
        if country_id_defaut:
            country_id_defaut = country_id_defaut[0]
        else:
            country_id_defaut = False

        # RAPPEL ÉQUIPE : on envoie un texto aux équipes si option activée.
        # Contrairement aux clients, pour les rendez-vous sur plusieurs jours,
        #   on envoie un texto de rappel tous les jours.
        for company in self.env['res.company'].sudo().search([]):
            if company.of_team_alert_intervention:
                for employee in self.env["hr.employee"].with_company(company).search([]):
                    message_body = "Your next interventions :\n"
                    interventions = intervention_obj.search(
                        [
                            ('of_employee_ids', 'in', [employee.id]),
                            ('start', '<=', end_date_reminder_str),
                            ('stop', '>=', tomorrow_date),
                            ('of_state', '=', 'confirmed'),
                        ],
                        order='start',
                    )
                    if not interventions:
                        continue

                    # On parcourt la liste des interventions.
                    for intervention in interventions:
                        date = fields.Datetime.context_timestamp(
                            intervention, fields.Datetime.from_string(intervention.date)
                        )
                        message_body += f"{date.day}/{date.month}/{date.year} {date.hour}h{date.minute}"
                        " (durée {intervention.duration}) : {intervention.name}\n"

                    employee._message_sms(body=message_body)

        # RAPPEL PARTICIPANT : On envoie un texto aux participants si option activée.
        for company in self.env['res.company'].sudo().search([]):
            if company.of_customer_alert_intervention:
                # On récupère les interventions du lendemain dont le rappel n'a pas déjà été effectué.
                interventions = intervention_obj.search(
                    [
                        ('start', '>=', tomorrow_date),
                        ('start', '<=', end_date_reminder_str),
                        ('of_state', '=', 'confirmed'),
                        ('of_is_customer_sms_sent', '=', False),
                    ],
                    order='start',
                )

                # On récupère le modèle de texto.
                if interventions:
                    sms_template = self.env.ref('of_sms.of_sms_planning_customer_appointment_reminder')

                for intervention in interventions:
                    intervention._message_sms_with_template(template=sms_template)
                    intervention.of_is_customer_sms_sent = True

        return True
