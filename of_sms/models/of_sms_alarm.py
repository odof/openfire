# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

import pytz
from datetime import datetime, timedelta, date

from odoo import api, fields, models, tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

def hour_to_str(hour):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return u"%02dh%02d" % (hour, round((hour % 1) * 60))

class OFPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _inherit = ["of.planning.intervention", 'mail.thread']

    def alerte_interventions_equipes_veille(self):
        return self.env['ir.values'].get_default('of.sms.config.settings', 'alerte_interventions_equipes_veille')

    def alerte_interventions_clients_veille(self):
        return self.env['ir.values'].get_default('of.sms.config.settings', 'alerte_interventions_clients_veille')

    def sms_notif_daily(self):
        d_today = fields.Date.from_string(fields.Date.today())
        d_tomorrow = d_today + timedelta(days=1)
        tz = pytz.timezone('Europe/Paris')
        str_tomorrow = d_tomorrow.strftime(DATE_FORMAT)
        dt_tomorrow_deb = tz.localize(datetime.strptime(str_tomorrow+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
        dt_tomorrow_fin = tz.localize(datetime.strptime(str_tomorrow+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
        intervention_obj = self.env["of.planning.intervention"]

        my_model = self.env['ir.model'].search([('model','=',"of.planning.intervention")])
        from_number = self.env["of.sms.number"].search([])
        if not from_number:
            _logger.error("sms_notif_daily failed: no number registered in 'of.sms.number'")
            return False
        from_number = from_number[0]
        if self.alerte_interventions_equipes_veille():
            equipes = self.env["of.planning.equipe"].search([])
            for equipe in equipes:
                message_body = u"Vos interventions de demain:"
                interventions = intervention_obj.search([('equipe_id', '=', equipe.id),
                                                         ('date', '<=', str_tomorrow),
                                                         ('date_deadline', '>=', str_tomorrow),
                                                         ('state', 'in', ('draft', 'confirm')),
                                                         ], order='date')
                if not interventions:
                    continue
                for intervention in interventions:
                    # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                    dt_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date))

                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    dt_local = max(dt_local, dt_tomorrow_deb)
                    dt_local = min(dt_local, dt_tomorrow_fin)
                    flo_local = round(dt_local.hour +
                                           dt_local.minute / 60.0 +
                                           dt_local.second / 3600.0, 5)
                    if flo_local <= 0.1:
                        continue
                    message_body += u"\n"
                    message_body += hour_to_str(flo_local) + u": " + intervention.tache_id.name + u", " + intervention.partner_city

                mobile_partners_to = equipe.employee_ids.mapped("user_id").mapped("partner_id").mapped("mobile")
                str_mobile_partners_to = ','.join(mobile_partners_to)

                #Queue the SMS message since we can't directly send MMS
                queued_sms = self.env['of.sms.message'].create({
                                                            'record_id': intervention.id,
                                                            'model_id': my_model[0].id,
                                                            'account_id':from_number.account_id.id,
                                                            'from_mobile':from_number.mobile_number,
                                                            'to_mobile':str_mobile_partners_to,
                                                            'sms_content':message_body,
                                                            'direction':'O',
                                                            'message_date':datetime.utcnow(),
                                                            'status_code': 'queued',
                                                            })
        if self.alerte_interventions_clients_veille():
            interventions = intervention_obj.search([('date', '<=', str_tomorrow),
                                                     ('date_deadline', '>=', str_tomorrow),
                                                     ('state', 'in', ('draft', 'confirm')),
                                                     ], order='date')
            for intervention in interventions:
                message_body = u"Rappel d'intervention: Demain (%s)" % (d_tomorrow.strftime("%d/%m/%Y"))
                # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                dt_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date))

                # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                #   (pour les interventions étalées sur plusieurs jours)
                dt_local = max(dt_local, dt_tomorrow_deb)
                dt_local = min(dt_local, dt_tomorrow_fin)
                flo_local = round(dt_local.hour +
                                       dt_local.minute / 60.0 +
                                       dt_local.second / 3600.0, 5)
                if flo_local <= 0.1:
                    continue
                message_body += u"\n"
                message_body += hour_to_str(flo_local) + u": " + intervention.tache_id.name + u", " + intervention.partner_city

                mobile_partner_to = intervention.partner_id.mobile

                #Queue the SMS message since we can't directly send MMS
                queued_sms = self.env['of.sms.message'].create({
                                                            'record_id': intervention.id,
                                                            'model_id': my_model[0].id,
                                                            'account_id':from_number.account_id.id,
                                                            'from_mobile':from_number.mobile_number,
                                                            'to_mobile':mobile_partner_to,
                                                            'sms_content':message_body,
                                                            'direction':'O',
                                                            'message_date':datetime.utcnow(),
                                                            'status_code': 'queued',
                                                            })

class OFSMSAlarmManager(models.AbstractModel):
    _name = "of.sms.alarm_manager"

    @api.model
    def send_sms_to_attendees(self,model_name,record_id):
        #_logger.error("sms alarm")
        sms_template = self.env['ir.model.data'].get_object('of_sms','sms_calendar_reminder')

        for attendee in event.partner_ids:
            if attendee.mobile:
                sms_template.sms_to = attendee.mobile
                self.env['of.sms.template'].send_sms(sms_template.id, event.id)
            else:
                _logger.warning("Attendee %s without mobile number" % attendee.name)

    @api.model
    def sms_notif_daily(self,model_names):
        for model_name in model_names:
            self.env[model_name].sms_notif_daily()

    @api.model
    def __send_sms_to_attendees(self,event):
        #_logger.error("sms alarm")
        sms_template = self.env['ir.model.data'].get_object('of_sms','sms_calendar_reminder')

        for attendee in event.partner_ids:
            if attendee.mobile:
                sms_template.sms_to = attendee.mobile
                self.env['of.sms.template'].send_sms(sms_template.id, event.id)
            else:
                _logger.warning("Attendee %s without mobile number" % attendee.name)

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _get_default_sms_recipients(self):
        """ Method overriden from mail.thread (defined in the sms module).
            SMS text messages will be sent to attendees that haven't declined the event(s).
        """
        return self.mapped('attendee_ids').filtered(lambda att: att.state != 'declined').mapped('partner_id')

    def _do_sms_reminder(self):
        #_logger.error("(OF) Do SMS Reminider")
        sms_template = self.env['ir.model.data'].get_object('of_sms','sms_calendar_reminder')

        for event in self:
            for attendee in event.partner_ids:
                if attendee.mobile:
                    sms_template.sms_to = attendee.mobile
                    le_self = self.with_context(tz='Europe/Paris')
                    le_self.env['of.sms.template'].send_sms(sms_template.id, event.id)
                    print self.env.user.tz
                else:
                    _logger.warning("Attendee %s without mobile number" % attendee.name)


class CalendarAlarmManagerSms(models.AbstractModel):
    _inherit = "calendar.alarm_manager"

    def get_next_potential_limit_alarm(self, alarm_type, seconds=None, partner_id=None):
        res = super(CalendarAlarmManagerSms,self).get_next_potential_limit_alarm(alarm_type, seconds, partner_id)
        """for prop in res:
            print str(prop) + ": "
            print "\n"
            "" "for prop_prop in prop:
                print "  " + str(prop_prop) + ": " + str(prop[prop_prop]) + "\n" " ""
            print "\n" """
        return res

    @api.model
    def get_next_mail(self):
        """ Cron method, overriden here to send SMS reminders as well """
        #_logger.error("Next Mail")
        result = super(CalendarAlarmManagerSms, self).get_next_mail()
        now = fields.Datetime.now()
        last_sms_cron = self.env['ir.config_parameter'].get_param('of_sms.last_sms_cron', default=now)
        cron = self.env['ir.model.data'].get_object('calendar', 'ir_cron_scheduler_alarm')

        interval_to_second = {
            "weeks": 7 * 24 * 60 * 60,
            "days": 24 * 60 * 60,
            "hours": 60 * 60,
            "minutes": 60,
            "seconds": 1
        }

        cron_interval = cron.interval_number * interval_to_second[cron.interval_type]
        events_data = self.get_next_potential_limit_alarm('sms', seconds=cron_interval)

        for event in self.env['calendar.event'].browse(events_data):
            max_delta = events_data[event.id]['max_duration']

            if event.recurrency:
                found = False
                for event_start in event._get_recurrent_date_by_event():
                    event_start = event_start.replace(tzinfo=None)
                    last_found = self.do_check_alarm_for_one_date(event_start, event, max_delta, 0, 'sms', after=last_sms_cron, missing=True)
                    for alert in last_found:
                        event.browse(alert['event_id'])._do_sms_reminder()
                        found = True
                    if found and not last_found:  # if the precedent event had an alarm but not this one, we can stop the search for this event
                        break
            else:
                #_logger.error("Event Reminder")
                event_start = fields.Datetime.from_string(event.start)
                for alert in self.do_check_alarm_for_one_date(event_start, event, max_delta, 0, 'sms', after=last_sms_cron, missing=True):
                    #_logger.error("sms reminider")
                    event.browse(alert['event_id'])._do_sms_reminder()
        self.env['ir.config_parameter'].set_param('of_sms.last_sms_cron', now)
        return result


class CalendarAlarm(models.Model):
    _inherit = "calendar.alarm"

    type = fields.Selection( selection_add=[("sms", "SMS")] )

