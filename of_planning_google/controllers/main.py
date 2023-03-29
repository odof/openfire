# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
from odoo.addons.google_calendar.controllers.main import GoogleCalendarController as google_calendar_controller


class GoogleCalendarController(google_calendar_controller):
    u"""Inheritance of 2 routes from google_calendar module in order to add OF planning implementation"""

    @http.route('/google_calendar/sync_data', type='json', auth='user')
    def sync_data(self, arch, fields, model, **kw):
        """ This route/function is called when we want to synchronize OpenFire Calendar with Google Calendar
            Function return a dictionary with the status :
                'need_config_from_admin', 'need_auth', 'need_refresh', 'success' if not calendar_event
            The dictionary may contain an url, to allow OpenERP Client to redirect user on this URL,
            for authorization for example
        """
        if model == 'of.planning.intervention':
            google_service_obj = request.env['google.service']
            google_planning_obj = request.env['google.planning']

            # Checking that admin have already configured Google API for Google synchronization !
            context = kw.get('local_context', {})
            client_id = google_service_obj.with_context(context).get_client_id('calendar')

            if not client_id or client_id == '':
                action_id = ''
                if google_planning_obj.can_authorize_google():
                    action_id = request.env.ref('google_calendar.action_config_settings_google_calendar').id
                return {
                    "status": "need_config_from_admin",
                    "url": '',
                    "action": action_id
                }

            # Checking that user have already accepted OpenERP to access his calendar !
            if google_planning_obj.need_authorize():
                url = google_planning_obj.with_context(context).authorize_google_uri(from_url=kw.get('fromurl'))
                return {
                    "status": "need_auth",
                    "url": url
                }

            user = request.env.user
            if not user.email:
                # Configuration of user email is done in res.partner form
                raise UserError(u"Your email needs to be set in your partner form")

            # If App authorized, and user access accepted, We launch the synchronization
            return google_planning_obj.with_context(context).synchronize_events()

        return super(GoogleCalendarController, self).sync_data(arch, fields, model, **kw)

    @http.route('/google_calendar/remove_references', type='json', auth='user')
    def remove_references(self, model, **kw):
        """This route/function is called when we want to empty Google Calendar fields from an OpenFire user"""
        if model == 'of.planning.intervention':
            google_planning_obj = request.env['google.planning']
            # Checking that user have already accepted OpenERP to access his calendar !
            context = kw.get('local_context', {})
            if google_planning_obj.with_context(context).remove_references():
                status = "OK"
            else:
                status = "KO"
            return status
        return super(GoogleCalendarController, self).remove_references(model, **kw)
