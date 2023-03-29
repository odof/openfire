# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from dateutil import parser
import json
import logging
import operator
import pytz
import urllib2

from odoo import api, fields, models, tools, _
from odoo.tools import exception_to_unicode
from odoo.exceptions import UserError

from odoo.addons.google_calendar.models.google_calendar \
    import status_response, Create, Update, Delete, NothingToDo, Exclude
from odoo.addons.of_utils.models.of_utils import hours_to_strs

_logger = logging.getLogger(__name__)


class Meta(type):
    """ This Meta class allow to define class as a structure, and so instancied variable
        in __init__ to avoid to have side effect alike 'static' variable """
    def __new__(typ, name, parents, attrs):
        methods = dict((k, v) for k, v in attrs.iteritems()
                       if callable(v))
        attrs = dict((k, v) for k, v in attrs.iteritems()
                     if not callable(v))

        def init(self, **kw):
            for key, val in attrs.iteritems():
                setattr(self, key, val)
            for key, val in kw.iteritems():
                assert key in attrs
                setattr(self, key, val)

        methods['__init__'] = init
        methods['__getitem__'] = getattr
        return type.__new__(typ, name, parents, methods)


class Struct(object):
    __metaclass__ = Meta


class OdooEvent(Struct):
    event = False
    found = False
    event_id = False
    isRecurrence = False
    isInstance = False
    update = False
    status = False
    attendee_id = False
    synchro = False


class GmailEvent(Struct):
    event = False
    found = False
    isRecurrence = False
    isInstance = False
    update = False
    status = False


class SyncEvent(object):
    def __init__(self):
        self.OE = OdooEvent()
        self.GG = GmailEvent()
        self.OP = None

    def __getitem__(self, key):
        return getattr(self, key)

    def compute_OP(self, modeFull=True):
        #If event are already in Gmail and in Odoo
        if self.OE.found and self.GG.found:
            #If the event has been deleted from one side, we delete on other side !
            if self.OE.status != self.GG.status:
                # if (self.OE.status and self.OE.update < self.GG.update) or
                # (self.GG.status and self.OE.update > self.GG.update):
                self.OP = Delete((self.OE.status and "OE") or (self.GG.status and "GG"),
                                 'The event has been deleted from one side, we delete on other side !')
            #If event is not deleted !
            elif self.OE.status and self.GG.status:
                if self.OE.update.split('.')[0] != self.GG.update.split('.')[0]:
                    if self.OE.update < self.GG.update:
                        tmpSrc = 'GG'
                    elif self.OE.update > self.GG.update:
                        tmpSrc = 'OE'
                    assert tmpSrc in ['GG', 'OE']

                    if self[tmpSrc].isRecurrence:
                        if self[tmpSrc].status:
                            self.OP = Update(tmpSrc, 'Only need to update, because i\'m active')
                        else:
                            self.OP = Exclude(tmpSrc, 'Need to Exclude (Me = First event from recurrence) from recurrence')

                    elif self[tmpSrc].isInstance:
                        self.OP = Update(tmpSrc, 'Only need to update, because already an exclu')
                    else:
                        self.OP = Update(tmpSrc, 'Simply Update... I\'m a single event')
                else:
                    if not self.OE.synchro or self.OE.synchro.split('.')[0] < self.OE.update.split('.')[0]:
                        self.OP = Update('OE', 'Event already updated by another user, but not synchro with my google calendar')
                    else:
                        self.OP = NothingToDo("", 'Not update needed')
            else:
                self.OP = NothingToDo("", "Both are already deleted")

        # New in Odoo...  Create on create_events of synchronize function
        elif self.OE.found and not self.GG.found:
            if self.OE.status:
                self.OP = Delete('OE', 'Update or delete from GOOGLE')
            else:
                if not modeFull:
                    self.OP = Delete('GG', 'Deleted from Odoo, need to delete it from Gmail if already created')
                else:
                    self.OP = NothingToDo("", "Already Deleted in gmail and unlinked in Odoo")
        elif self.GG.found and not self.OE.found:
            tmpSrc = 'GG'
            if not self.GG.status and not self.GG.isInstance:
                # don't need to make something... because event has been created and deleted before the synchronization
                self.OP = NothingToDo("", 'Nothing to do... Create and Delete directly')
            else:
                if self.GG.isInstance:
                    if self[tmpSrc].status:
                        self.OP = Exclude(tmpSrc, 'Need to create the new exclu')
                    else:
                        self.OP = Exclude(tmpSrc, 'Need to copy and Exclude')
                else:
                    self.OP = Create(tmpSrc, 'New EVENT CREATE from GMAIL')

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        event_str = "\n\n---- A SYNC EVENT ---"
        event_str += "\n    ID          OE: %s " % (self.OE.event and self.OE.event.id)
        event_str += "\n    ID          GG: %s " % (self.GG.event and self.GG.event.get('id', False))
        event_str += "\n    Name        OE: %s " % (self.OE.event and self.OE.event.name.encode('utf8'))
        event_str += "\n    Name        GG: %s " % (self.GG.event and self.GG.event.get('summary', '').encode('utf8'))
        event_str += "\n    Found       OE:%5s vs GG: %5s" % (self.OE.found, self.GG.found)
        event_str += "\n    Recurrence  OE:%5s vs GG: %5s" % (self.OE.isRecurrence, self.GG.isRecurrence)
        event_str += "\n    Instance    OE:%5s vs GG: %5s" % (self.OE.isInstance, self.GG.isInstance)
        event_str += "\n    Synchro     OE: %10s " % (self.OE.synchro)
        event_str += "\n    Update      OE: %10s " % (self.OE.update)
        event_str += "\n    Update      GG: %10s " % (self.GG.update)
        event_str += "\n    Status      OE:%5s vs GG: %5s" % (self.OE.status, self.GG.status)
        if (self.OP is None):
            event_str += "\n    Action      %s" % "---!!!---NONE---!!!---"
        else:
            event_str += "\n    Action      %s" % type(self.OP).__name__
            event_str += "\n    Source      %s" % (self.OP.src)
            event_str += "\n    comment     %s" % (self.OP.info)
        return event_str


class GooglePlanning(models.AbstractModel):
    u"""Modified copy of google.calendar model"""
    STR_SERVICE = 'calendar'
    _name = 'google.planning'

    def generate_data(self, interv, is_creating=False):
        u"""Generate Google Calendar event dict out of Odoo event
            :param interv: of.planning.intervention record
            :param is_creating: indicates and event creation rather than an update
        """
        tz = pytz.timezone(self._context.get('tz') or 'Europe/Paris')
        interv = interv.sudo()
        if interv.all_day:
            # Convert to local timezone before set dates
            start_utc_dt = pytz.UTC.localize(fields.Datetime.from_string(interv.date_prompt))
            start_local_dt = start_utc_dt.astimezone(tz)
            start_date = fields.Date.to_string(start_local_dt)
            end_utc_dt = pytz.UTC.localize(fields.Datetime.from_string(interv.date_deadline_prompt))
            # Date to google needs to be 1 day later because end date is exclusive
            end_local_dt = end_utc_dt.astimezone(tz) + timedelta(days=1)
            final_date = fields.Date.to_string(end_local_dt)
            type = 'date'
            vstype = 'dateTime'
        else:
            start_date = fields.Datetime.context_timestamp(
                self, fields.Datetime.from_string(interv.date_prompt)).isoformat('T')
            final_date = fields.Datetime.context_timestamp(
                self, fields.Datetime.from_string(interv.date_deadline_prompt)).isoformat('T')
            type = 'dateTime'
            vstype = 'date'
        attendee_default = self.env.ref('of_planning_google.employee_google', raise_if_not_found=False)
        attendee_default_id = attendee_default and attendee_default.id or -1
        attendee_list = []
        # add interv employees and partner and other partners
        for employee in interv.employee_ids:
            if employee.id == attendee_default_id:
                continue
            email = tools.email_split(employee.email_synchro)
            email = email[0] if email else 'NoEmail@mail.com'
            attendee_dict = {
                'email': email,
                'displayName': employee.name,
            }
            if employee.user_id.id == self.env.user.id:
                attendee_dict['self'] = True
            attendee_list.append(attendee_dict)
        for partner in interv.partner_ids:
            email = tools.email_split(partner.email)
            email = email[0] if email else 'NoEmail@mail.com'
            attendee_dict = {
                'email': email,
                'displayName': partner.name,
            }
            if self.env.user.id in partner.user_ids.ids:
                attendee_dict['self'] = True
            attendee_list.append(attendee_dict)

        data = {
            'summary': interv.name or '',
            'description': interv.description or '',
            'start': {
                type: start_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or 'Europe/Paris',
            },
            'end': {
                type: final_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or 'Europe/Paris',
            },
            'attendees': attendee_list,
            'location': interv.address_id and interv.address_id._display_address() or '',
        }
        if is_creating:
            data['creator'] = {'email': interv.create_uid.email, 'displayName': interv.create_uid.name}
            if interv.create_uid.id == self.env.user.id:
                data['creator']['self'] = True
        if interv.user_id:
            data['organizer'] = {'email': interv.user_id.email, 'displayName': interv.user_id.name}
            if interv.user_id.id == self.env.user.id:
                data['organizer']['self'] = True
        if interv.recurrency and interv.rrule:
            data['recurrence'] = ['RRULE:' + interv.rrule]

        if not interv.active or interv.state in ('cancel', 'postponed'):
            data['status'] = 'cancelled'
        elif interv.state in ('confirmed', 'done', 'unfinished', 'during'):
            data['status'] = 'confirmed'
        else:
            data['status'] = 'tentative'

        return data

    def create_an_event(self, interv):
        """ Create a new event in google calendar from the given event in Odoo
            :param interv: of.planning.intervention record to export to google calendar
        """
        data = self.generate_data(interv, is_creating=True)

        url = '/calendar/v3/calendars/%s/events?fields=%s&access_token=%s' % (
            'primary', urllib2.quote('id,updated'), self.get_token())
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = json.dumps(data)
        return self.env['google.service']._do_request(url, data_json, headers, type='POST')

    def delete_an_event(self, event_id):
        """ Delete the given event in primary calendar of google cal
            :param event_id : google cal identifier of the event to delete
        """
        params = {
            'access_token': self.get_token()
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = '/calendar/v3/calendars/%s/events/%s' % ('primary', event_id)

        # OF -> To prevent data loss we temporarily inactivate Google event deletion, may be reactivated later
        # We keep the possibility to reactivate the deletion by adding a config parameter
        allow_deletion = self.env['ir.config_parameter'].get_param('of.planning.google.allow.deletion', default=False)
        if allow_deletion:
            return self.env['google.service']._do_request(url, params, headers, type='DELETE')
        else:
            return True

    def get_calendar_primary_id(self):
        """ In google calendar, you can have multiple calendar. But only one is
            the 'primary' one. This Calendar identifier is 'primary'.
        """
        params = {
            'fields': 'id',
            'access_token': self.get_token()
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = '/calendar/v3/calendars/primary'

        try:
            status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')
        except urllib2.HTTPError, e:
            if e.code == 401:  # Token invalid / Acces unauthorized
                error_msg = _(u"[OF] Your token is invalid or has been revoked !")

                self.env.user.write({'google_calendar_token': False, 'google_calendar_token_validity': False})
                self.env.cr.commit()

                raise self.env['res.config.settings'].get_config_warning(error_msg)
            raise

        return status_response(status), content['id'] or False, ask_time

    def get_event_synchro_dict(self, lastSync=False, token=False, nextPageToken=False):
        """ Returns events on the 'primary' calendar from google cal.
            :return: dict where the key is the google_cal event id, and the value the details of the event,
                    defined at https://developers.google.com/google-apps/calendar/v3/reference/events/list
        """
        if not token:
            token = self.get_token()

        params = {
            'fields': 'items,nextPageToken',
            'access_token': token,
            'maxResults': 1000,
        }

        if lastSync:
            params['updatedMin'] = lastSync.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            params['showDeleted'] = True
        else:
            params['timeMin'] = self.get_minTime().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = '/calendar/v3/calendars/%s/events' % 'primary'
        if nextPageToken:
            params['pageToken'] = nextPageToken

        status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')

        google_events_dict = {}
        for google_event in content['items']:
            google_events_dict[google_event['id']] = google_event

        if content.get('nextPageToken'):
            google_events_dict.update(
                self.get_event_synchro_dict(lastSync=lastSync, token=token, nextPageToken=content['nextPageToken'])
            )

        return google_events_dict

    def get_one_event_synchro(self, google_id):
        token = self.get_token()

        params = {
            'access_token': token,
            'maxResults': 1000,
            'showDeleted': True,
        }

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = '/calendar/v3/calendars/%s/events/%s' % ('primary', google_id)
        try:
            status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')
        except Exception, e:
            _logger.info(u"[OF] Calendar Synchro - In except of get_one_event_synchro")
            _logger.info(exception_to_unicode(e))
            return False

        return status_response(status) and content or False

    def update_to_google(self, oe_event, google_event):
        url = '/calendar/v3/calendars/%s/events/%s?fields=%s&access_token=%s' % (
            'primary', google_event['id'], 'id,updated', self.get_token())
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data = self.generate_data(oe_event)
        data['sequence'] = google_event.get('sequence', 0)
        data_json = json.dumps(data)

        status, content, ask_time = self.env['google.service']._do_request(url, data_json, headers, type='PATCH')

        google_synchro_date = datetime.strptime(content['updated'], '%Y-%m-%dT%H:%M:%S.%fz')
        oe_event.write({
            'google_synchro_date': google_synchro_date,
            'google_upload_fail': False,
        })

    def update_recurrent_event_exclu(self, instance_id, event_ori_google_id, event_new):
        """ Update detached occurence of a odoo recurring event to google calendar
            :param instance_id : new google cal identifier
            :param event_ori_google_id : origin google cal identifier
            :param event_new : of.planning.intervention record that has been detached
        """
        data = self.generate_data(event_new)
        url = '/calendar/v3/calendars/%s/events/%s?access_token=%s' % ('primary', instance_id, self.get_token())
        headers = {'Content-type': 'application/json'}

        data.update(
            recurringEventId=event_ori_google_id, originalStartTime=event_new.recurrent_id_date,
            sequence=self.get_sequence(instance_id))

        # OF -> To prevent data loss we temporarily inactivate Google occurrence deletion, may be reactivated later
        # We keep the possibility to reactivate the deletion by adding a config parameter
        allow_deletion = self.env['ir.config_parameter'].get_param('of.planning.google.allow.deletion', default=False)
        if data['status'] == 'cancelled' and not allow_deletion:
            data['status'] = 'tentative'

        data_json = json.dumps(data)

        return self.env['google.service']._do_request(url, data_json, headers, type='PUT')

    def create_from_google(self, event):
        u"""Create of.planning.intervention record out of google event dict

        :param event: SyncEvent, see module google_calendar
        :return: updated SyncEvent
        """
        context_tmp = dict(self._context, NewMeeting=True)
        # failsafe : test if GG event is already connected to an odoo event; if so, do not create
        existing_interv = self.with_context(active_test=False).env['of.planning.intervention'].sudo().search(
            [('google_internal_event_id', '=', event.GG.event['id'])], limit=1)
        if existing_interv:
            res = self.with_context(context_tmp).update_from_google(existing_interv, event.GG.event, 'write')
        else:
            res = self.with_context(context_tmp).update_from_google(False, event.GG.event, 'create')
        event.OE.event_id = res
        interv = self.env['of.planning.intervention'].sudo().browse(res)
        if interv.rrule:
            excluded_recurrent_event_ids = self.env['of.planning.intervention'].sudo().search(
                [('google_internal_event_id', '=ilike', '%s\_%%' % event.GG.event['id'])])
            for detached in excluded_recurrent_event_ids:
                detached.write(
                    {'recurrent_id': interv.id, 'recurrent_id_date': detached.date, 'user_id': interv.user_id.id})
        return event

    def update_from_google(self, interv, single_event_dict, update_type):
        """ Update an event in Odoo with information from google calendar
            :param interv: of.planning.intervention record to update, False if update type is 'create'
            :param single_event_dict: dict of google cal event data
            :param update_type: type of operation to be done, either 'create', 'write' or 'copy'

            :return res: interv id
        """
        res = False
        interv_obj = self.env['of.planning.intervention'].sudo().with_context(no_mail_to_attendees=True)
        partner_obj = self.env['res.partner'].sudo()

        if not self.env.user.email:
            raise UserError(u"Your email needs to be set in your partner form")
        employees = self.env['hr.employee'].sudo().search(
            [('email_synchro', '=', self.env.user.email),
             '|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)])
        employee_record = [(6, 0, employees.ids)]
        duree = 0.5
        partner_record = [(5,)]
        result = {}
        user_email = single_event_dict.get('organizer', single_event_dict.get('creator', {})).get('email')
        user = False
        if user_email:
            user = self.env['res.users'].sudo().search([('email', '=', user_email)], limit=1)
            if user:
                result['user_id'] = user.id
        if not user:
            user = self.env.user
        # separate operators from other participants
        emp_op_list, partner_list, not_found_list = self.get_of_attendee_from_gg_attendee(
            single_event_dict.get('attendees', []), interv)

        for not_found in not_found_list:
            data = {
                'email': not_found.get('email'),
                'customer': False,
            }
            name = not_found.get('displayName', False) or not_found.get('email')
            if hasattr(partner_obj, 'lastname'):
                data['lastname'] = name
            else:
                data['name'] = name
            new_partner = partner_obj.create(data)
            partner_record.append((4, new_partner.id))

        if emp_op_list:
            employee_record += [(4, emp_id) for emp_id in emp_op_list]

        if partner_list:
            partner_record += [(4, part_id) for part_id in partner_list]

        if len(employee_record) == 1 and not employee_record[0][2]:
            if user_email:
                # there was no attendee at this event, we look to see if organizer is an op employee
                intervenants = self.env['hr.employee'].sudo().search([
                    ('email_synchro', '=', user_email),
                    '|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)])
                if intervenants:
                    employee_record += [(4, emp_id) for emp_id in intervenants.ids]
        if len(employee_record) == 1 and not employee_record[0][2]:
            # no op employee in attendees, we add default google op employee
            employee_google = self.env.ref('of_planning_google.employee_google')
            employee_record = [(6, 0, [employee_google.id])]

        UTC = pytz.timezone('UTC')
        if single_event_dict.get('start') and single_event_dict.get('end'):  # If not cancelled
            allday = False
            if single_event_dict['start'].get('dateTime', False) and single_event_dict['end'].get('dateTime', False):
                start = parser.parse(single_event_dict['start']['dateTime'])
                stop = parser.parse(single_event_dict['end']['dateTime'])
                duree = (stop - start).seconds / 3600.0
                start = str(start.astimezone(UTC))[:-6]
                stop = str(stop.astimezone(UTC))[:-6]
            elif single_event_dict['start'].get('date', False) and single_event_dict['end'].get('date', False):
                allday = True
                start = single_event_dict['start']['date']
                stop = single_event_dict['end']['date']
                d_end = fields.Date.from_string(stop)
                # end date coming from Google is exclusive, so we substract 1 day
                d_end = d_end + timedelta(days=-1)
                stop = fields.Date.to_string(d_end)

                # Calculate start and end dates depending on attendees timetables
                employee_ids = []
                for rec in employee_record:
                    if rec[0] == 6:
                        employee_ids += rec[2]
                    elif rec[0] == 4:
                        employee_ids.append(rec[1])
                if employee_ids:
                    employees = self.env['hr.employee'].sudo().browse(list(set(employee_ids)))
                    start_date_emp_timetables = employees.get_horaires_date(start)
                    if not any(start_date_emp_timetables[e] for e in start_date_emp_timetables):
                        # No timetable for this day
                        start_time = self.env['ir.values'].get_default(
                            'of.intervention.settings', 'calendar_min_time') or 0.0
                    else:
                        start_time = min(
                            [start_date_emp_timetables[e] and start_date_emp_timetables[e][0][0] or 24.0
                             for e in start_date_emp_timetables])

                    end_date_emp_timetables = employees.get_horaires_date(stop)
                    if not any(end_date_emp_timetables[e] for e in end_date_emp_timetables):
                        # No timetable for this day
                        end_time = self.env['ir.values'].get_default(
                            'of.intervention.settings', 'calendar_max_time') or 24.0
                    else:
                        end_time = max(
                            [end_date_emp_timetables[e] and end_date_emp_timetables[e][-1][-1] or 0.0
                             for e in end_date_emp_timetables])
                else:
                    start_time = self.env['ir.values'].get_default(
                        'of.intervention.settings', 'calendar_min_time') or 0.0
                    end_time = self.env['ir.values'].get_default(
                        'of.intervention.settings', 'calendar_max_time') or 24.0

                start_time_str = hours_to_strs('time', start_time)[0]
                if end_time == 24.0:
                    end_time_str = '23:59'
                else:
                    end_time_str = hours_to_strs('time', end_time)[0]

                tz = pytz.timezone(interv.tz or self.env.context.get('tz'))

                start_datetime_str = '%s %s:00' % (start, start_time_str)
                start_datetime = tz.localize(datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M:%S'))
                start_datetime_utc = start_datetime.astimezone(UTC)
                start = fields.Datetime.to_string(start_datetime_utc)

                end_datetime_str = '%s %s:00' % (stop, end_time_str)
                end_datetime = tz.localize(datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M:%S'))
                end_datetime_utc = end_datetime.astimezone(UTC)
                stop = fields.Datetime.to_string(end_datetime_utc)

            else:
                start = u""
                stop = u""
                duree = 0.0

            if start and stop and duree:
                result.update({
                    'date': start,
                    'date_deadline_forcee': stop,
                    'duree': duree,
                    'forcer_dates': True,
                    'all_day': allday,
                })
            else:
                _logger.error(
                    u"[OF] Calendar Synchro - Event dictionnary received from google has incoherency in its dates"
                    u"GG event id: %s ; OF event id: %s ; start: %s ; stop: %s ; duration: %f" % (
                        single_event_dict.get('id'), str(interv and interv.id), start, stop, duree))

        description = single_event_dict.get('description', u"")
        google_synchro_date = datetime.strptime(single_event_dict['updated'], '%Y-%m-%dT%H:%M:%S.%fz')

        # For module V1, we do not synchronize address_id field with Google location
        result['google_address'] = single_event_dict.get('location', False)
        # address = False
        # if location:
        #     # try to find a partner with this address
        #     loc_args = location.split(', ')
        #     if len(loc_args) == 3:
        #         # google address format: street, zip city, country
        #         street = loc_args[0]
        #         street2 = street
        #         zipcode = loc_args[1][:5]
        #         city = loc_args[1][6:]
        #     elif len(loc_args) == 4:
        #         # google address format: street2, street, zip city, country
        #         street2 = loc_args[0]
        #         street = loc_args[1]
        #         zipcode = loc_args[2][:5]
        #         city = loc_args[2][6:]
        #     if len(loc_args) in (3, 4):
        #         address = partner_obj.search(
        #             [('city', '=ilike', city),
        #              ('zip', '=', zipcode),
        #              '|',
        #                  '|', ('street', '=ilike', street), ('street2', '=ilike', street),
        #                  '|', ('street', '=ilike', street2), ('street2', '=ilike', street2)],
        #             limit=1)
        # if address:
        #     result['address_id'] = address.id
        # else:
        #     result['google_address'] = location

        result.update({
            'employee_ids': employee_record,
            'partner_ids': partner_record,
            'name': single_event_dict.get('summary', _(u"Google event")),
            'description': description,
            'google_synchro_date': google_synchro_date,
            'google_internal_event_id': single_event_dict.get('id'),
            'verif_dispo': False,
        })

        if single_event_dict.get('recurrence', False):
            rrule = [rule for rule in single_event_dict['recurrence'] if rule.startswith('RRULE:')][0][6:]
            result['rrule'] = rrule

        try:
            if update_type == 'write':
                interv.with_context(no_google_synchro_update=True).write(result)
                res = interv.id
            elif update_type == 'copy':  # detach 1
                interv = interv.detach_recurring_event(values=result)
                res = interv.id
            elif update_type == 'create':
                user_sudo = self.env['res.users'].sudo().browse(user.id)
                company_sudo_obj = self.env['res.company'].sudo()
                company = company_sudo_obj.browse(user_sudo.of_google_company_id and user_sudo.of_google_company_id.id)
                if not company:
                    company = company_sudo_obj._company_default_get('of.planning.intervention')
                    if not company:
                        company = company_sudo_obj._company_default_get('account.account')
                result.update({
                    'origin_interface': u"Google Agenda",
                    'google_create': True,
                    'state': 'draft',
                    'company_id': company.id,
                    'tache_id': self.env.ref('of_planning_google.tache_google', raise_if_not_found=False).id,
                    'type_id': self.env.ref('of_planning_recurring.of_service_type_misc', raise_if_not_found=False).id,
                })
                interv = interv_obj.create(result)
                res = interv.id
            if interv:
                try:
                    interv.onchange_company_id()
                    _logger.debug(u"[OF] Event %s updated correctly by user %s" % (
                        interv.name, self.env.user.name))
                except Exception, e:
                    _logger.error(
                        u"[OF] Calendar Synchro : error during update from google at onchange stage\n "
                        u"message:\n%s" % e.message)
        except Exception, e:
            _logger.error(
                u"[OF] Calendar Synchro : error during update from google at create/write stage\n "
                u"message:\n%s" % e.message)

        return res

    def get_of_attendee_from_gg_attendee(self, gg_attendee_list, interv):
        """Split google attendees between opertor employees, partners and attendees not existing in DB.

        :param gg_attendee_list: list of attendees received from google event dict
        :param interv: If given, iterate first on it's employees to save time
        :return: [
            emp_op_list (to be added to operator employees),
            partner_list (to be added to partners),
            not_found_list (to be created in DB)
        ]
        """
        # We check first employees, then users, then partners
        employee_obj = self.env['hr.employee'].sudo()
        user_obj = self.env['res.users'].sudo()
        partner_obj = self.env['res.partner'].sudo()
        emp_op_list = []
        partner_list = []
        not_found_list = []
        all_employees = employee_obj.search([])
        op_employees = all_employees.filtered(lambda emp: emp.of_est_commercial or emp.of_est_intervenant)
        # filter out employees that don't have user because ultimately participants that are not ops are partners
        not_op_employees = (all_employees - op_employees).filtered(lambda emp: emp.user_id)
        for gg_attendee in gg_attendee_list:
            email = gg_attendee.get('email', False)
            if email == 'NoEmail@mail.com':
                email = ''
            name = gg_attendee.get('displayName', email)
            if not email and not name:
                # neither a valid email nor a name, we shouldn't be here
                continue

            if interv:
                found = False
                # check first interv employees to save iterations
                for interv_employee in interv['employee_ids']:
                    if interv_employee.email_synchro == email:
                        emp_op_list.append(interv_employee.id)
                        found = True
                        break
                    elif interv_employee.name == name:
                        emp_op_list.append(interv_employee.id)
                        found = True
                        break
                if found:
                    continue

            if email:
                for employee in op_employees:
                    if employee.email_synchro == email:
                        emp_op_list.append(employee.id)
                        break
                else:
                    for employee in not_op_employees:
                        if employee.email_synchro == email:
                            partner_list.append(employee.user_id.partner_id.id)
                            break
                    else:
                        partner = partner_obj.search([('email', '=', email)], limit=1)
                        if partner:
                            partner_list.append(partner.id)
                        else:
                            not_found_list.append(gg_attendee)
            else:
                for employee in op_employees:
                    if employee.name == email:
                        emp_op_list.append(employee.id)
                        break
                    user = employee.user_id
                    if user:
                        if user.name == name:
                            emp_op_list.append(employee.id)
                            break
                        elif hasattr(user_obj, 'lastname') and (user.lastname == name or user.firstname == name):
                            emp_op_list.append(employee.id)
                            break
                else:
                    for employee in not_op_employees:
                        if employee.name == name:
                            partner_list.append(employee.user_id.partner_id.id)
                            break
                        user = employee.user_id
                        if user.name == name:
                            partner_list.append(user.partner_id.id)
                            break
                        elif hasattr(user_obj, 'lastname') and (user.lastname == name or user.firstname == name):
                            partner_list.append(user.partner_id.id)
                            break
                    else:
                        domain = [('name', 'like', name)]
                        if hasattr(partner_obj, 'lastname'):
                            domain = ['|', '|', ('firstname', 'like', name), ('lastname', 'like', name)] + domain
                        partner = partner_obj.search(domain, limit=1)
                        if partner:
                            partner_list.append(partner.id)
                        else:
                            not_found_list.append(gg_attendee)
        return emp_op_list, partner_list, not_found_list

    def remove_references(self):
        current_user = self.env.user
        reset_data = {
            'google_calendar_rtoken': False,
            'google_calendar_token': False,
            'google_calendar_token_validity': False,
            'google_calendar_last_sync_date': False,
            'of_google_calendar_last_sync_date': False,
            'google_calendar_cal_id': False,
        }

        return current_user.write(reset_data)

    @api.model
    def synchronize_events_cron(self):
        """ Call by the cron. """
        users = self.env['res.users'].sudo().search([('of_google_calendar_last_sync_date', '!=', False)])
        _logger.info(u"[OF] Calendar Synchro - Started by cron")

        for user_to_sync in users.ids:
            _logger.info(u"[OF] Calendar Synchro - Starting synchronization for a new user [%s]", user_to_sync)
            try:
                resp = self.sudo(user_to_sync).with_context(from_cron=True).synchronize_events(last_sync=True)
                if resp.get('status') == 'need_reset':
                    _logger.info(u"[OF] [%s] Calendar Synchro - Failed - NEED RESET  !", user_to_sync)
                else:
                    _logger.info(
                        u"[OF] [%s] Calendar Synchro - Done with status : %s  !", user_to_sync, resp.get('status'))
            except Exception, e:
                _logger.info(u"[OF] [%s] Calendar Synchro - Exception : %s !", user_to_sync, exception_to_unicode(e))
        _logger.info(u"[OF] Calendar Synchro - Ended by cron")

    def synchronize_events(self, last_sync=True):
        """ Entry point for synchronization. """
        user_to_sync = self.env.uid
        current_user = self.env.user

        status, current_google, ask_time = self.get_calendar_primary_id()
        if current_user.google_calendar_cal_id:
            if current_google != current_user.google_calendar_cal_id:
                return {
                    'status': 'need_reset',
                    'info': {
                        'old_name': current_user.google_calendar_cal_id,
                        'new_name': current_google
                    },
                    'url': '',
                }

            if last_sync and self.get_last_sync_date() and not self.is_force_full_synchro():
                last_sync = self.get_last_sync_date()
                _logger.info(
                    u"[OF] [%s] Calendar Synchro - MODE SINCE_MODIFIED : %s !",
                    user_to_sync, fields.Datetime.to_string(last_sync))
            else:
                last_sync = False
                _logger.info(u"[OF] [%s] Calendar Synchro - MODE FULL SYNCHRO FORCED", user_to_sync)
        else:
            current_user.write({'google_calendar_cal_id': current_google})
            last_sync = False
            _logger.info(u"[OF] [%s] Calendar Synchro - MODE FULL SYNCHRO - NEW CAL ID", user_to_sync)

        new_ids = []
        new_ids += self.create_new_events()
        new_ids += self.bind_recurring_events_to_google()

        res, interv_cant_upload = self.update_events(last_sync)

        current_user.write({'of_google_calendar_last_sync_date': ask_time})
        # @todo: replace with a tag on the event to avoid having the popup each time we synchronize
        if interv_cant_upload:
            # At least one interv could not be uploaded because of access rights restriction on Google side
            interv_cant_upload.write({'google_upload_fail': True})
            return {
                'status': 'interv_cant_upload',
                'url': '',
                'interv_list': [[i.name, i.user_id.name, str(i.id)] for i in interv_cant_upload],
            }
        return {
            'status': res and 'need_refresh' or 'no_new_event_from_google',
            'url': '',
        }

    def create_new_events(self):
        """ Create event in google calendar for the intervs not already synchronized, for the current user.
            :return: list of newly-created event identifiers in google calendar
        """
        new_ids = []
        employee = self.env['hr.employee'].sudo().search([('email_synchro', '=', self.env.user.email)])
        # at this point there is necessarily a partner with user email
        partner = self.env['res.partner'].sudo().search([('email', '=', self.env.user.email)])

        # user can be in 4 differents fields
        interventions = self.env['of.planning.intervention'].sudo().with_context(virtual_id=False).search(
            [
                ('google_internal_event_id', '=', False),
                '|', '|', '|',
                ('employee_ids', 'in', employee.ids),
                ('user_id', '=', self.env.user.id),
                ('partner_id', '=', partner and partner[0].id),
                ('partner_ids', 'in', partner.ids),
                '|',
                ('date_deadline', '>', fields.Datetime.to_string(self.get_minTime())),
                ('final_date', '>', fields.Datetime.to_string(self.get_minTime())),
            ])
        for interv in interventions:
            if not interv.recurrent_id or interv.recurrent_id == 0:
                status, response, ask_time = self.create_an_event(interv)
                if status_response(status):
                    google_synchro_date = datetime.strptime(response['updated'], '%Y-%m-%dT%H:%M:%S.%fz')
                    interv.write({
                        'google_synchro_date': google_synchro_date,
                        'google_internal_event_id': response['id']})
                    new_ids.append(response['id'])
                    self.env.cr.commit()
                else:
                    _logger.warning(
                        u"[OF] Impossible to create event %s. [%s] Enable DEBUG for response detail.",
                        interv.id, status)
                    _logger.debug(u"Response : %s", response)
        return new_ids

    def get_context_no_virtual(self):
        """ get the current context modified to prevent virtual ids and active test. """
        return dict(self.env.context, virtual_id=False, active_test=False)

    def bind_recurring_events_to_google(self):
        """ Connects detached occurences of odoo recurring events that have not yet been connected """
        new_ids = []
        interv_obj = self.env['of.planning.intervention'].sudo()
        context_norecurrent = self.get_context_no_virtual()
        employees = self.env['hr.employee'].sudo().search(
            [('email_synchro', '=', self.env.user.email),
             '|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)])
        # at this point there is necessarily a partner with user email
        partner = self.env['res.partner'].sudo().search([('email', '=', self.env.user.email)])
        detached_intervs = interv_obj.with_context(context_norecurrent).search(
            [
                ('google_internal_event_id', '=', False),
                ('recurrent_id', '!=', False),
                ('recurrent_id', '!=', 0),
                '|', '|', '|',
                ('user_id', '=', self.env.user.id),
                ('employee_ids', 'in', employees.ids),
                ('partner_id', '=', partner and partner[0].id),
                ('partner_ids', 'in', partner.ids),
            ])
        for interv in detached_intervs:
            new_google_internal_event_id = False
            source_interv = interv_obj.search([('id', '=', interv.recurrent_id)])
            if not source_interv:
                # source_interv has been unlinked or deactivated
                continue

            if interv.recurrent_id_date and source_interv.all_day and source_interv.google_internal_event_id:
                new_google_internal_event_id = '%s_%s' % (
                    source_interv.google_internal_event_id, interv.recurrent_id_date.split(' ')[0].replace('-', ''))
            elif interv.recurrent_id_date and source_interv.google_internal_event_id:
                new_google_internal_event_id = '%s_%sZ' % (
                    source_interv.google_internal_event_id,
                    interv.recurrent_id_date.replace('-', '').replace(' ', 'T').replace(':', ''))

            if new_google_internal_event_id:
                #TODO WARNING, NEED TO CHECK THAT EVENT and ALL instance NOT DELETE IN GMAIL BEFORE !
                try:
                    status, response, ask_time = self.update_recurrent_event_exclu(
                        new_google_internal_event_id, source_interv.google_internal_event_id, interv)
                    if status_response(status):
                        interv.write({'google_internal_event_id': new_google_internal_event_id})
                        new_ids.append(new_google_internal_event_id)
                        self.env.cr.commit()
                    else:
                        _logger.warning(u"[OF] Impossible to create event %s. [%s]", interv.id, status)
                        _logger.debug(u"Response : %s", response)
                except:
                    pass

        return new_ids

    def update_events(self, lastSync=False):
        """ Synchronize events with google calendar : fetching, creating, updating, deleting, ... """
        interv_obj = self.env['of.planning.intervention'].sudo()
        my_partner_id = self.env.user.partner_id.id
        employees = self.env['hr.employee'].sudo().search([('email_synchro', '=', self.env.user.email)])
        context_novirtual = self.get_context_no_virtual()

        if lastSync:
            # only update events that have been updated since last sync date, on one side or the other
            try:
                all_event_from_google = self.get_event_synchro_dict(lastSync=lastSync)
            except urllib2.HTTPError, e:
                if e.code == 410:  # GONE, Google is lost.
                    # we need to force the rollback from this cursor,
                    # because it locks my res_users, but I need to write in this tuple before to raise.
                    self.env.cr.rollback()
                    self.env.user.write({'of_google_calendar_last_sync_date': False})
                    self.env.cr.commit()
                error_key = json.loads(str(e))
                error_key = error_key.get('error', {}).get('message', 'nc')
                error_msg = _(u"[OF] Google is lost... the next synchro will be a full synchro. \n\n %s") % error_key
                raise self.env['res.config.settings'].get_config_warning(error_msg)

            interv_upd_from_google = interv_obj.with_context(context_novirtual).search([
                '|', '|', '|',
                ('user_id', '=', self.env.user.id),
                ('employee_ids', 'in', employees.ids),
                ('partner_id', '=', my_partner_id),
                ('partner_ids', 'in', my_partner_id),
                ('google_internal_event_id', 'in', all_event_from_google.keys())
            ])
            upd_gg_ids = interv_upd_from_google.ids

            interv_upd_from_odoo = interv_obj.with_context(context_novirtual).search([
                '|', '|', '|',
                ('user_id', '=', self.env.user.id),
                ('employee_ids', 'in', employees.ids),
                ('partner_id', '=', my_partner_id),
                ('partner_ids', 'in', my_partner_id),
                '|',
                ('google_synchro_date', '>', fields.Datetime.to_string(lastSync)),
                ('google_upload_fail', '=', True),
                ('google_internal_event_id', '!=', False),
            ])

            my_odoo_googleinternal_records = interv_upd_from_odoo.read(['id', 'google_internal_event_id'])

            if self.get_print_log():
                _logger.info(
                    u"[OF] Calendar Synchro -  \n\nUPDATE IN GOOGLE\n%s\n\nRETRIEVE FROM OE\n%s\n\nUPDATE IN "
                    u"OE\n%s\n\nRETRIEVE FROM GG\n%s\n\n", all_event_from_google, upd_gg_ids, interv_upd_from_odoo.ids,
                    my_odoo_googleinternal_records)

            for gi_record in my_odoo_googleinternal_records:
                active = True  # if not sure, we request google
                if gi_record.get('id'):
                    active = interv_obj.with_context(context_novirtual).browse(int(gi_record.get('id'))).active

                if gi_record.get('google_internal_event_id') \
                        and not all_event_from_google.get(gi_record.get('google_internal_event_id')) and active:
                    # add google event id to the dict of google event ids to be considered
                    one_event = self.get_one_event_synchro(gi_record.get('google_internal_event_id'))
                    if one_event:
                        all_event_from_google[one_event['id']] = one_event

            interventions = (interv_upd_from_google | interv_upd_from_odoo)

        else:
            # update all events regardless of possible last sync date
            domain = [
                '|', '|', '|',
                ('user_id', '=', self.env.user.id),
                ('employee_ids', 'in', employees.ids),
                ('partner_id', '=', my_partner_id),
                ('partner_ids', 'in', my_partner_id),
                ('google_internal_event_id', '!=', False),
                '|',
                ('date_deadline', '>', fields.Datetime.to_string(self.get_minTime())),
                ('final_date', '>', fields.Datetime.to_string(self.get_minTime())),
            ]

            # Select all events from Odoo which have been already synchronized in gmail
            interventions = interv_obj.with_context(context_novirtual).search(domain)
            all_event_from_google = self.get_event_synchro_dict(lastSync=False)

        # this dict will be made of SyncEvents, see module google_calendar
        event_to_synchronize = {}
        user_synchro_date = self.env.user.of_google_calendar_last_sync_date
        for interv in interventions:
            # first build OE side of sync events
            base_event_id = interv.google_internal_event_id.rsplit('_', 1)[0]

            if base_event_id not in event_to_synchronize:
                event_to_synchronize[base_event_id] = {}

            if interv.google_internal_event_id not in event_to_synchronize[base_event_id]:
                event_to_synchronize[base_event_id][interv.google_internal_event_id] = SyncEvent()

            ev_to_sync = event_to_synchronize[base_event_id][interv.google_internal_event_id]

            ev_to_sync.OE.attendee_id = interv.employee_main_id.id
            ev_to_sync.OE.event = interv
            ev_to_sync.OE.found = True
            ev_to_sync.OE.event_id = interv.id
            ev_to_sync.OE.isRecurrence = interv.recurrency
            ev_to_sync.OE.isInstance = bool(interv.recurrent_id and interv.recurrent_id > 0)
            ev_to_sync.OE.update = interv.google_synchro_date
            ev_to_sync.OE.status = interv.active
            # if interv has been synchronised by another user more recently, then we take current user synchro date
            if user_synchro_date and interv.google_synchro_date:
                if user_synchro_date < interv.google_synchro_date:
                    synchro = user_synchro_date
                else:
                    synchro = interv.google_synchro_date
            else:
                synchro = user_synchro_date or interv.google_synchro_date
            ev_to_sync.OE.synchro = synchro

        for event in all_event_from_google.values():
            # then build google side of sync events
            event_id = event.get('id')
            base_event_id = event_id.rsplit('_', 1)[0]

            if base_event_id not in event_to_synchronize:
                event_to_synchronize[base_event_id] = {}

            if event_id not in event_to_synchronize[base_event_id]:
                event_to_synchronize[base_event_id][event_id] = SyncEvent()

            ev_to_sync = event_to_synchronize[base_event_id][event_id]

            ev_to_sync.GG.event = event
            ev_to_sync.GG.found = True
            ev_to_sync.GG.isRecurrence = bool(event.get('recurrence', ''))
            ev_to_sync.GG.isInstance = bool(event.get('recurringEventId', 0))
            ev_to_sync.GG.update = event.get('updated', None)  # if deleted, no date without browse event
            if ev_to_sync.GG.update:
                ev_to_sync.GG.update = ev_to_sync.GG.update.replace('T', ' ').replace('Z', '')[:19]
            ev_to_sync.GG.status = (event.get('status') != 'cancelled')

        ######################
        #   PRE-PROCESSING   #
        ######################
        for base_event in event_to_synchronize:
            # compute_OP will define what to do about this event : update on OF side, update on GG side, delete, etc.
            # see module google_calendar for detail
            for current_event in event_to_synchronize[base_event]:
                event_to_synchronize[base_event][current_event].compute_OP(modeFull=not lastSync)
            if self.get_print_log():
                if not isinstance(event_to_synchronize[base_event][current_event].OP, NothingToDo):
                    _logger.info(event_to_synchronize[base_event])

        ######################
        #      DO ACTION     #
        ######################
        # User may not have the access right necessary to update an event from OF to GA,
        # we sync what we can and keep track of events in error
        interv_cant_upload = self.env['of.planning.intervention'].sudo()
        for base_event in event_to_synchronize:
            event_to_synchronize[base_event] = sorted(
                event_to_synchronize[base_event].iteritems(), key=operator.itemgetter(0))
            for current_event in event_to_synchronize[base_event]:
                self.env.cr.commit()
                event = current_event[1]  # event is a SyncEvent !
                # Recompute OP in case occurrence has been fully deleted in the meantime
                if event.OE.event_id and not interv_obj.with_context(context_novirtual).search(
                        [('id', '=', event.OE.event_id)]):
                    event.OE.found = False
                    event.compute_OP(modeFull=not lastSync)

                actToDo = event.OP
                actSrc = event.OP.src

                # To avoid redefining 'self', all method below should use 'recs' instead of 'self'
                recs = self

                if isinstance(actToDo, NothingToDo):
                    continue
                elif isinstance(actToDo, Create):
                    if actSrc == 'GG':
                        self.create_from_google(event)
                    elif actSrc == 'OE':
                        raise u"Should be never here, creation for OE is done before update !"
                    #TODO Add to batch
                elif isinstance(actToDo, Update):
                    if actSrc == 'GG':
                        recs.update_from_google(event.OE.event, event.GG.event, 'write')
                    elif actSrc == 'OE':
                        if event.OE.event.google_upload_fail and self._context.get('from_cron'):
                            # do not update automatiquely events that have been flagged.
                            # else, when the cron syncs as the user_id of flagged intervs,
                            # updates made in odoo by another user will be uploaded to google
                            # instead, we'd rather have said user_id check the edit and sync by hand
                            interv_cant_upload |= event.OE.event
                            continue
                        try:
                            recs.update_to_google(event.OE.event, event.GG.event)
                        except UserError:
                            if event.OE.event.user_id and event.OE.event.user_id.id == self.env.user.id:
                                # When, on google side, we delete an event permanently, and then try to update it,
                                # even as the owner, we get a 403 error (returned as UserError).
                                # In that case, unlink from odoo (deactivate)
                                event.OE.event.unlink()
                            else:
                                interv_cant_upload |= event.OE.event
                elif isinstance(actToDo, Exclude):
                    if actSrc == 'OE':
                        recs.delete_an_event(current_event[0])
                    elif actSrc == 'GG':
                        new_google_event_id = ''
                        if '_' in event.GG.event['id'] and '_R' not in event.GG.event['id']:
                            new_google_event_id = event.GG.event['id'].rsplit('_', 1)[1]
                            if 'T' in new_google_event_id:
                                new_google_event_id = new_google_event_id.replace('T', '')[:-1]
                            else:
                                new_google_event_id = new_google_event_id + '000000'

                        if not event_to_synchronize[base_event][0][1].OE.event_id:
                            main_ev = interv_obj.with_context(context_novirtual).search(
                                [('google_internal_event_id', '=', event.GG.event['id'].rsplit('_', 1)[0])],
                                limit=1)
                            event_to_synchronize[base_event][0][1].OE.event_id = main_ev.id

                        interv_id = event_to_synchronize[base_event][0][1].OE.event_id
                        if interv_id and new_google_event_id:
                            interv_id = '%s-%s' % (interv_id, new_google_event_id)

                        if event.GG.status:
                            if interv_id:
                                parent_interv = interv_obj.browse(interv_id)
                                recs.update_from_google(parent_interv, event.GG.event, 'copy')
                            else:
                                recs.create_from_google(event)
                        elif interv_id:
                            google_synchro_date = datetime.strptime(event.GG.event['updated'], '%Y-%m-%dT%H:%M:%S.%fz')
                            interv_obj.browse(interv_id).\
                                with_context(
                                google_internal_event_id=event.GG.event.get('id'),
                                google_synchro_date=google_synchro_date).\
                                unlink(can_be_deleted=False)

                elif isinstance(actToDo, Delete):
                    if actSrc == 'GG':
                        try:
                            # Deleted from Odoo, need to delete it from Google if already created
                            recs.delete_an_event(current_event[0])
                        except urllib2.HTTPError, e:
                            # if already deleted from gmail or never created
                            if e.code in (401, 410,):
                                pass
                            else:
                                raise e
                    elif actSrc == 'OE':
                        inter = interv_obj.browse(event.OE.event_id)
                        # If occurrence, test if it must be archived or deleted
                        recurrent_inter = False
                        all_dates = []
                        if inter.recurrent_id:
                            recurrent_inter = interv_obj.browse(inter.recurrent_id)
                            all_dates = map(
                                lambda dt: fields.Datetime.to_string(dt),
                                recurrent_inter._get_all_recurrent_date_by_event())
                        if recurrent_inter and inter.recurrent_id_date not in all_dates:
                            inter.with_context(of_force_occ_unlink=True).unlink(can_be_deleted=True)
                        else:
                            google_synchro_date = datetime.strptime(event.GG.event['updated'], '%Y-%m-%dT%H:%M:%S.%fz')
                            interv_obj.browse(event.OE.event_id).with_context(google_synchro_date=google_synchro_date).\
                                unlink(can_be_deleted=False)

        return True, interv_cant_upload

    def get_sequence(self, instance_id):
        params = {
            'fields': 'sequence',
            'access_token': self.get_token()
        }
        headers = {'Content-type': 'application/json'}
        url = '/calendar/v3/calendars/%s/events/%s' % ('primary', instance_id)
        status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')
        return content.get('sequence', 0)

    #################################
    ##  MANAGE CONNEXION TO GMAIL  ##
    #################################

    def get_token(self):
        current_user = self.env.user
        if not current_user.google_calendar_token_validity \
                or fields.Datetime.from_string(current_user.google_calendar_token_validity.split('.')[0]) \
                < (datetime.now() + timedelta(minutes=1)):
            self.do_refresh_token()
            current_user.refresh()
        return current_user.google_calendar_token

    def get_last_sync_date(self):
        current_user = self.env.user
        return current_user.of_google_calendar_last_sync_date and fields.Datetime.from_string(
            current_user.of_google_calendar_last_sync_date) + timedelta(minutes=0) or False

    def do_refresh_token(self):
        current_user = self.env.user
        all_token = self.env['google.service']._refresh_google_token_json(
            current_user.google_calendar_rtoken, self.STR_SERVICE)

        vals = {}
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(
            seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')

        self.env.user.sudo().write(vals)

    def need_authorize(self):
        current_user = self.env.user
        return current_user.google_calendar_rtoken is False

    def get_calendar_scope(self, RO=False):
        readonly = '.readonly' if RO else ''
        return 'https://www.googleapis.com/auth/calendar%s' % (readonly)

    def authorize_google_uri(self, from_url='http://www.odoo.com'):
        url = self.env['google.service']._get_authorize_uri(from_url, self.STR_SERVICE, scope=self.get_calendar_scope())
        return url

    def can_authorize_google(self):
        return self.env['res.users'].sudo().has_group('base.group_erp_manager')

    @api.model
    def set_all_tokens(self, authorization_code):
        all_token = self.env['google.service']._get_google_token_json(authorization_code, self.STR_SERVICE)

        vals = {}
        vals['google_%s_rtoken' % self.STR_SERVICE] = all_token.get('refresh_token')
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(
            seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')
        self.env.user.sudo().write(vals)

    def get_minTime(self):
        number_of_week = self.env['ir.config_parameter'].get_param('calendar.week_synchro', default=5)
        return datetime.now() - timedelta(weeks=int(number_of_week))

    def is_force_full_synchro(self):
        # would be set by hand for testing.
        return self.env['ir.config_parameter'].get_param('calendar.force_full_synchro', default=False)

    def get_print_log(self):
        return self.env['ir.config_parameter'].get_param('calendar.debug_print', default=False)
