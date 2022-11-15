# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import collections
from dateutil import parser
from dateutil import rrule
from operator import itemgetter
from datetime import datetime, timedelta
import pytz
import re

from odoo import api, models, fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

from odoo.addons.calendar.models.calendar import VIRTUALID_DATETIME_FORMAT, calendar_id2real_id, get_real_ids, \
    real_id2calendar_id, is_calendar_id
from odoo.addons.of_utils.models.of_utils import heures_minutes_2_float, format_date


class OFPlanningRecurringMixin(models.AbstractModel):
    u"""Interface pour permettre d'ajouter facilement le principe de récurrence sur les RDV et le wizard de modif"""
    _name = 'of.planning.recurring.mixin'

    # on reprend les noms de champs définis dans of_planning pour faciliter les choses
    date = fields.Datetime(string=u"Date de début")
    date_deadline = fields.Datetime(string=u"Date de fin")
    all_day = fields.Boolean(string=u"Toute la journée")

    active = fields.Boolean(string=u"Actif", default=True)
    # RECURRENCE FIELDS
    rrule_display = fields.Text(string=u"Règles de récurrence", compute='_compute_rrule_display')
    rrule = fields.Char(string=u"Règle de récurrence", compute='_compute_rrule', inverse='_inverse_rrule', store=True)
    rrule_type = fields.Selection([
        ('daily', u"Jour(s)"),
        ('weekly', u"Semaine(s)"),
        ('monthly', u"Mois"),
        ('yearly', u"Année(s)")
    ], string=u"type d'intervalle", default='weekly',
        help=u"type d'intervalle entre 2 occurences de ce RDV. hebdomadaire par défaut")
    recurrency = fields.Boolean(string=u"Recurrent", help=u"RDV récurrent")
    recurrent_id = fields.Integer(string=u"ID du recurrent associé", index=True)
    # Champ occurrence_ids à surcharger dans les héritages de la classe abstraite
    occurrence_ids = fields.One2many(
        comodel_name='of.planning.recurring.mixin', inverse_name='recurrent_id', string=u"Occurrences")
    recurrent_id_date = fields.Datetime(string=u"Date du recurrent associé")
    end_type = fields.Selection([
        ('count', u"nombre de répétitions"),
        ('end_date', u"date de fin")
    ], string=u"Fin de la récurrence", default='count')
    interval = fields.Integer(
        string=u"Répéter chaque", default=1, help=u"Répéter tous les x (Jours/Semaines/Mois/Années)")
    count = fields.Integer(string=u"Compteur de répétition", help=u"Répéter x fois", default=1)
    mo = fields.Boolean(string=u"Lun")
    tu = fields.Boolean(string=u"Mar")
    we = fields.Boolean(string=u"Mer")
    th = fields.Boolean(string=u"Jeu")
    fr = fields.Boolean(string=u"Ven")
    sa = fields.Boolean(string=u"Sam")
    su = fields.Boolean(string=u"Dim")
    month_by = fields.Selection([
        ('date', u"Nº du jour"),
        ('day', u"Jour du mois")
    ], string=u'Option', default='date')
    day = fields.Integer(string=u"Nº du jour", default=1)
    week_list = fields.Selection([
        ('MO', u"Lundi"),
        ('TU', u"Mardi"),
        ('WE', u"Mercredi"),
        ('TH', u"Jeudi"),
        ('FR', u"Vendredi"),
        ('SA', u"Samedi"),
        ('SU', u"Dimanche")
    ], string=u"Jour de la semaine")
    byday = fields.Selection([
        ('1', u"Premier"),
        ('2', u"Deuxième"),
        ('3', u"Troisième"),
        ('4', u"Quatrième"),
        ('5', u"Cinquième"),
        ('-1', u"Dernier")
    ], string=u"Par jour")
    final_date = fields.Date(string=u"Répéter jusqu'à")

    # COMPUTE

    @api.depends('byday', 'recurrency', 'final_date', 'rrule_type', 'month_by', 'interval', 'count', 'end_type', 'mo',
                 'tu', 'we', 'th', 'fr', 'sa', 'su', 'day', 'week_list', 'all_day')
    def _compute_rrule_display(self):
        u""" Gets Recurrence rule string, human-readable."""
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for meeting in self:
            if not meeting.recurrency or not meeting.rrule_type:
                meeting.rrule_display = u""
            else:
                rrule_text = u""
                if meeting.rrule_type == 'weekly':
                    rrule_text += u"Toutes les "
                else:
                    rrule_text += u"Tous les "
                if meeting.interval > 1:
                    rrule_text += (str(meeting.interval)).decode('utf-8') + u" "
                if meeting.rrule_type == 'weekly':
                    rrule_text += u"semaines, les "
                    first_day = False
                    if meeting.mo:
                        rrule_text += u"lundi"
                        first_day = True
                    if meeting.tu:
                        rrule_text += (u", " if first_day else u"") + u"mardi"
                        first_day = True
                    if meeting.we:
                        rrule_text += (u", " if first_day else u"") + u"mercredi"
                        first_day = True
                    if meeting.th:
                        rrule_text += (u", " if first_day else u"") + u"jeudi"
                        first_day = True
                    if meeting.tu:
                        rrule_text += (u", " if first_day else u"") + u"vendredi"
                        first_day = True
                    if meeting.tu:
                        rrule_text += (u", " if first_day else u"") + u"samedi"
                        first_day = True
                    if meeting.tu:
                        rrule_text += (u", " if first_day else u"") + u"dimanche"
                elif meeting.rrule_type == 'daily':
                    rrule_text += u"jours"
                elif meeting.rrule_type == 'monthly':
                    rrule_text += u"mois, le "
                    if meeting.month_by == 'date':
                        if meeting.day == 1:
                            rrule_text += u"1er "
                        else:
                            rrule_text += (str(meeting.day)).decode('utf-8') + u" "
                    else:
                        numero = _(dict(self._fields['byday'].selection)[meeting.byday]).lower()
                        jour = _(dict(self._fields['week_list'].selection)[meeting.week_list]).lower()
                        rrule_text += u"%s %s " % (numero, jour)
                    rrule_text += u" du mois"
                elif meeting.rrule_type == 'yearly':
                    rrule_text += u"ans"
                rrule_text += u"\n"
                if meeting.end_type == 'count':
                    rrule_text += u"%s fois à partir du %s" % (meeting.count, format_date(meeting.date_date, lang))
                else:
                    rrule_text += u"Entre le %s et le %s" % (
                        format_date(meeting.date_date, lang), format_date(meeting.final_date, lang))
                rrule_text += u"\n"
                if meeting.all_day:
                    rrule_text += u"Toute la journée"
                else:
                    rrule_text += u"De %s à %s" % (meeting.heure_debut_str, meeting.heure_fin_str)
                meeting.rrule_display = rrule_text

    @api.depends('byday', 'recurrency', 'final_date', 'rrule_type', 'month_by', 'interval', 'count', 'end_type', 'mo',
                 'tu', 'we', 'th', 'fr', 'sa', 'su', 'day', 'week_list')
    def _compute_rrule(self):
        u"""Gets Recurrence rule string according to value type RECUR of iCalendar from the values given."""
        for meeting in self:
            if meeting.recurrency:
                meeting.rrule = meeting._rrule_serialize()
            else:
                meeting.rrule = ''

    @api.multi
    def _inverse_rrule(self):
        for meeting in self:
            if meeting.rrule:
                data = self._rrule_default_values()
                data['recurrency'] = True
                data.update(self._rrule_parse(meeting.rrule, data, meeting.date))
                meeting.update(data)

    # @API.CONSTRAINS

    @api.constrains('recurrency', 'end_type', 'count')
    def check_alert_count_zero(self):
        for interv in self:
            if interv.recurrency and interv.end_type == 'count' and not interv.count:
                raise UserError(
                    _(u"Oupsy! On dirait que vous avez oublié d'indiquer un nombre de répétitions."))

    # ONCHANGE

    @api.onchange('rrule_type')
    def _onchange_rrule_type(self):
        self.ensure_one()
        # self.date is the date stored in DB, not the calculated date of this occurence
        if self.date:
            if self.rrule_type == 'weekly':
                dt = datetime.strptime(self.date, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)
                day_int = dt.isoweekday()
                int_2_field_dict = {
                    1: 'mo',
                    2: 'tu',
                    3: 'we',
                    4: 'th',
                    5: 'fr',
                    6: 'sa',
                    7: 'su',
                }
                # décocher tous les jours non concernés et cocher le jour concerné
                update_vals = {int_2_field_dict[day_cmp]: (day_cmp == day_int) for day_cmp in range(1, 8)}
                self.update(update_vals)
            elif self.rrule_type == 'monthly':
                dt = datetime.strptime(self.date, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)
                self.update({'month_by': 'date', 'day': dt.day})

    # AUTRES

    @api.model
    def _get_recurrent_fields(self):
        return ['byday', 'recurrency', 'final_date', 'rrule_type', 'month_by',
                'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa',
                'su', 'day', 'week_list']

    @api.multi
    def _get_recurrent_dates_by_event(self):
        u""" Get recurrent start and stop dates based on Rule string """
        start_dates = self._get_recurrent_date_by_event(date_field='date')
        stop_dates = self._get_recurrent_date_by_event(date_field='date_deadline')
        return zip(start_dates, stop_dates)

    @api.multi
    def _get_recurrent_date_by_event(self, date_field='date'):
        u""" Get recurrent dates based on Rule string and all event where recurrent_id is child

        :param date_field: the field containing the reference date information for recurrency computation
        """
        self.ensure_one()
        if date_field in self._fields.keys() and self._fields[date_field].type in ('date', 'datetime'):
            reference_date = self[date_field]
        else:
            # date field stored in DB, NOT this occurence date
            reference_date = self.date

        def todate(date_eval):
            val = parser.parse(''.join((re.compile('\d')).findall(date_eval)))
            # Dates are localized to saved timezone if any, else current timezone.
            if not val.tzinfo:
                val = pytz.UTC.localize(val)
            return val.astimezone(timezone)

        timezone = pytz.timezone(self._context.get('tz') or 'UTC')
        event_date = pytz.UTC.localize(fields.Datetime.from_string(reference_date))  # Add "+hh:mm" timezone
        if not event_date:
            event_date = datetime.now()

        use_naive_datetime = self.all_day and self.rrule and 'UNTIL' in self.rrule and 'Z' not in self.rrule
        if not use_naive_datetime:
            # Convert the event date to saved timezone (or context tz) as it'll
            # define the correct hour/day asked by the user to repeat for recurrence.
            event_date = event_date.astimezone(timezone)  # transform "+hh:mm" timezone

        # The start date is naive
        # the timezone will be applied, if necessary, at the very end of the process
        # to allow for DST timezone reevaluation
        rset1 = rrule.rrulestr(str(self.rrule), dtstart=event_date.replace(tzinfo=None), forceset=True, ignoretz=True)

        # récupérer les éventuels RDV issus de RDV récurrents et détachés
        recurring_meetings = self.with_context(active_test=False).occurrence_ids

        for meeting in recurring_meetings:
            date = fields.Datetime.from_string(meeting.recurrent_id_date)
            if use_naive_datetime:
                date = date.replace(tzinfo=None)
            else:
                date = todate(meeting.recurrent_id_date).replace(tzinfo=None)
            if date_field.startswith('date_deadline'):
                date = date + timedelta(hours=self.duree)
            # exclure la date de ce RDV des occurrences du RDV récurrent
            rset1._exdate.append(date)
        def naive_tz_to_utc(d):
            return timezone.localize(d).astimezone(pytz.UTC)

        return [naive_tz_to_utc(d) if not use_naive_datetime else d for d in rset1]

    @api.multi
    def _get_recurrency_end_date(self, format_dt=False):
        u""" Return the last date a recurring event happens, according to its end_type. """
        self.ensure_one()

        if not self.recurrency:
            return False

        end_type = self.end_type
        final_date = self.final_date
        if end_type == 'count' and all(self[key] for key in ['count', 'rrule_type', 'date_deadline', 'interval']):
            all_rec_dates = self._get_recurrent_date_by_event()
            if format_dt:
                return all_rec_dates and all_rec_dates[-1]
            final_date = all_rec_dates and fields.Datetime.to_string(all_rec_dates[-1])
        elif format_dt:
            final_date = fields.Datetime.from_string(final_date)
        return final_date

    @api.multi
    def _rrule_serialize(self, force_values={}):
        u""" Compute rule string according to value type RECUR of iCalendar
            :param force_values: dictionary containing values to replace record field values.
            :return: string containing recurring rule (empty if no rule)
        """
        rec_field_list = self._get_recurrent_fields()
        # populate values with record values when necessary
        values = {}
        for field_name in rec_field_list:
            values[field_name] = force_values.get(field_name, self[field_name])

        if values['interval'] and values['interval'] < 0:
            raise UserError(_('interval cannot be negative.'))
        if values['count'] and values['count'] <= 0:
            raise UserError(_('Event recurrence interval cannot be negative.'))

        def get_week_string(freq):
            weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
            if freq == 'weekly':
                byday = [field.upper() for field in weekdays if values[field]]
                if byday:
                    return ';BYDAY=' + ','.join(byday)
            return ''

        def get_month_string(freq):
            if freq == 'monthly':
                if values['month_by'] == 'date' and (values['day'] < 1 or values['day'] > 31):
                    raise UserError(_("Please select a proper day of the month."))
                # Eg : Second Monday of the month
                if values['month_by'] == 'day' and values['byday'] and values['week_list']:
                    return ';BYDAY=' + values['byday'] + values['week_list']
                elif values['month_by'] == 'date':  # Eg : 16th of the month
                    return ';BYMONTHDAY=' + str(values['day'])
            return ''

        def get_end_date():
            end_date_new = ''.join(
                (re.compile('\d')).findall(values['final_date'])) + 'T235959Z' if values['final_date'] else False
            return (values['end_type'] == 'count' and (';COUNT=' + str(values['count'])) or '') + \
                   ((end_date_new and values['end_type'] == 'end_date' and (';UNTIL=' + end_date_new)) or '')

        freq = values['rrule_type']  # day/week/month/year
        result = ''
        if freq:
            interval_srting = values['interval'] and (';INTERVAL=' + str(values['interval'])) or ''
            result = 'FREQ=' + freq.upper() + get_week_string(
                freq) + interval_srting + get_end_date() + get_month_string(freq)
        return result

    def _rrule_default_values(self):
        return {
            'byday': False,
            'recurrency': False,
            'final_date': False,
            'rrule_type': False,
            'month_by': False,
            'interval': 0,
            'count': False,
            'end_type': False,
            'mo': False,
            'tu': False,
            'we': False,
            'th': False,
            'fr': False,
            'sa': False,
            'su': False,
            'day': False,
            'week_list': False
        }

    def _rrule_parse(self, rule_str, data, date_start):
        day_list = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        rrule_type = ['yearly', 'monthly', 'weekly', 'daily']
        ddate = fields.Datetime.from_string(date_start)
        if 'Z' in rule_str and not ddate.tzinfo:
            ddate = ddate.replace(tzinfo=pytz.timezone('UTC'))
            rule = rrule.rrulestr(rule_str, dtstart=ddate, cache=True)
        else:
            rule = rrule.rrulestr(rule_str, dtstart=ddate, cache=True)

        if rule._freq > 0 and rule._freq < 4:
            data['rrule_type'] = rrule_type[rule._freq]
        data['count'] = rule._count
        data['interval'] = rule._interval
        data['final_date'] = rule._until and rule._until.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # repeat weekly
        if rule._byweekday:
            for i in xrange(0, 7):
                if i in rule._byweekday:
                    data[day_list[i]] = True
            data['rrule_type'] = 'weekly'
        # repeat monthly by nweekday ((weekday, weeknumber), )
        if rule._bynweekday:
            data['week_list'] = day_list[list(rule._bynweekday)[0][0]].upper()
            data['byday'] = str(list(rule._bynweekday)[0][1])
            data['month_by'] = 'day'
            data['rrule_type'] = 'monthly'

        if rule._bymonthday:
            data['day'] = list(rule._bymonthday)[0]
            data['month_by'] = 'date'
            data['rrule_type'] = 'monthly'

        # repeat yearly but for openerp it's monthly, take same information as monthly but interval is 12 times
        if rule._bymonth:
            data['interval'] = data['interval'] * 12

        # FIXME handle forever case
        # end of recurrence
        # in case of repeat for ever that we do not support right now
        if not (data.get('count') or data.get('final_date')):
            data['count'] = 100
        if data.get('count'):
            data['end_type'] = 'count'
        else:
            data['end_type'] = 'end_date'
        return data


class OFPlanningIntervention(models.Model):
    _inherit = ['of.planning.intervention', 'of.planning.recurring.mixin']
    _name = 'of.planning.intervention'

    jour_ids = fields.Many2many(
        string=u"Jours", comodel_name='of.jours', relation='of_interv_recurring_jour_rel',
        column1='intervention_id', column2='jour_id', compute='_compute_jour_ids')
    occurrence_ids = fields.One2many(
        comodel_name='of.planning.intervention', inverse_name='recurrent_id', string=u"Occurrences")

    # @API.DEPENDS

    @api.depends('recurrency', 'rrule')
    def _compute_tournee_ids(self):
        tournee_obj = self.env['of.planning.tournee']
        unique_ids = list(set([calendar_id2real_id(interv_id) for interv_id in self.ids]))
        self = self.browse(unique_ids)
        interv_rec = self.filtered(lambda i: i.recurrency)
        # le champ 'active' est passé à False uniquement lorsqu'on 'unlink' une occurence
        interv_others = self.filtered(lambda i: not i.recurrency and i.active)
        super(OFPlanningIntervention, interv_others)._compute_tournee_ids()
        for intervention in interv_rec.filtered(lambda i: i.state not in ('cancel', 'postponed')):
            datetime_couples = intervention._get_recurrent_dates_by_event()
            all_dates = []
            for dt_tup in datetime_couples:
                deb_str = fields.Date.to_string(dt_tup[0])
                fin_str = fields.Date.to_string(dt_tup[1])
                all_dates.append(deb_str)
                if deb_str != fin_str:
                    current_da = fields.Date.from_string(deb_str) + timedelta(days=1)
                    fin_da = fields.Date.from_string(fin_str)
                    while current_da <= fin_da:
                        all_dates.append(fields.Date.to_string(current_da))
                        current_da += timedelta(days=1)
            tournees = tournee_obj.search([
                ('employee_id', 'in', intervention.employee_ids.ids),
                ('date', 'in', all_dates)])
            intervention.tournee_ids = [(6, 0, tournees.ids)]
        for interv_no_tournee in self.filtered(lambda i: not i.active or i.state in ('cancel', 'postponed')):
            interv_no_tournee.tournee_ids = [(5, 0, 0)]

    @api.depends('mo', 'tu', 'we', 'th', 'fr', 'sa', 'su')
    def _compute_jour_ids(self):
        jour_obj = self.env['of.jours']
        for interv in self:
            jour_num_list = interv.get_jour_num()
            jours = jour_obj.search([('numero', 'in', jour_num_list)])
            interv.jour_ids = jours.ids

    def get_jour_num(self):
        field_names = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        res = []
        for i in range(7):
            if self[field_names[i]]:
                res.append(i+1)
        return res

    # ONCHANGE

    @api.onchange('type_id')
    def _onchange_type_id(self):
        self.ensure_one()
        if self.type_id and self.type_id != self.env.ref('of_planning_recurring.of_service_type_misc'):
            self.recurrency = False

    @api.onchange('verif_dispo')
    def _onchange_verif_dispo(self):
        self.ensure_one()
        if self.recurrency:
            self.verif_dispo = False

    @api.onchange('recurrency')
    def _onchange_recurrency(self):
        self.ensure_one()
        type_misc_id = self.env.ref('of_planning_recurring.of_service_type_misc').id
        # les RDVs réguliers sont de type "Divers"
        if self.recurrency:
            update_vals = {'verif_dispo': False, 'forcer_dates': True}
            if not self.type_id or self.type_id != type_misc_id:
                update_vals['type_id'] = type_misc_id
            self.update(update_vals)
            self._onchange_rrule_type()

    # HÉRITAGES

    @api.multi
    def get_metadata(self):
        real = self.browse(set({x: calendar_id2real_id(x) for x in self.ids}.values()))
        return super(OFPlanningIntervention, real).get_metadata()

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        for arg in args:
            if arg[0] == 'id':
                for n, calendar_id in enumerate(arg[2]):
                    if isinstance(calendar_id, basestring):
                        # récupérer l'id réel
                        arg[2][n] = calendar_id.split('-')[0]
        return super(OFPlanningIntervention, self)._name_search(
            name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.multi
    def write(self, values):
        if not self.user_has_groups('of_planning_recurring.of_group_planning_intervention_recurring'):
            return super(OFPlanningIntervention, self).write(values)
        if values.get('recurrency'):
            values['verif_dispo'] = False
        # process events one by one
        for meeting in self:
            # special write of complex IDS
            real_ids = []
            if not is_calendar_id(meeting.id):
                real_ids = [int(meeting.id)]
            else:
                real_event_id = calendar_id2real_id(meeting.id)

                # if we are setting the recurrency flag to False or if we are only changing fields that
                # should be only updated on the real ID and not on the virtual (like message_follower_ids):
                # then set real ids to be updated.
                blacklisted = any(key in values for key in ('date', 'date_deadline_forcee', 'active'))
                # aussi détacher si on annule
                blacklisted = blacklisted or values.get('state') == 'cancel'
                if not values.get('recurrency', True) or not blacklisted:
                    real_ids = [real_event_id]
                else:
                    data = meeting.read(['date_prompt', 'date_deadline_prompt', 'rrule', 'duree'])[0]
                    if data.get('rrule'):
                        meeting.with_context(dont_notify=True).detach_recurring_event(values)

            real_meetings = self.browse(real_ids)
            super(OFPlanningIntervention, real_meetings).write(values)

            # set end_date for calendar searching
            if any(field in values
                   for field in ['recurrency', 'end_type', 'count', 'rrule_type', 'date', 'date_deadline_forcee']):
                for real_meeting in real_meetings:
                    if real_meeting.recurrency and real_meeting.end_type in ('count', unicode('count')):
                        final_date = real_meeting._get_recurrency_end_date()
                        super(OFPlanningIntervention, real_meeting).write({'final_date': final_date})
        return True

    @api.multi
    def _write(self, vals):
        if not self.user_has_groups('of_planning_recurring.of_group_planning_intervention_recurring'):
            return super(OFPlanningIntervention, self)._write(vals)
        # process events one by one
        for meeting in self:
            # special write of complex IDS
            real_ids = []
            if not is_calendar_id(meeting.id):
                real_ids = [int(meeting.id)]
            else:
                real_event_id = calendar_id2real_id(meeting.id)

                # if we are setting the recurrency flag to False or if we are only changing fields that
                # should be only updated on the real ID and not on the virtual (like message_follower_ids):
                # then set real ids to be updated.
                blacklisted = any(key in vals for key in ('date', 'date_deadline', 'active'))
                if not vals.get('recurrency', True) or not blacklisted:
                    real_ids = [real_event_id]

            real_meetings = self.browse(real_ids)
            super(OFPlanningIntervention, real_meetings)._write(vals)

        return True

    @api.model
    def create(self, values):
        if 'user_id' not in values:  # Else bug with quick_create when we are filter on an other user
            values['user_id'] = self.env.user.id
        if values.get('recurrency'):
            values['verif_dispo'] = False

        meeting = super(OFPlanningIntervention, self).create(values)

        if not values.get('final_date'):
            final_date = meeting._get_recurrency_end_date()
            # `dont_notify=True` in context to prevent multiple notify_next_alarm
            meeting.with_context(dont_notify=True).write({'final_date': final_date})
        return meeting

    @api.multi
    def export_data(self, fields_to_export, raw_data=False):
        u""" Override to convert virtual ids to ids """
        records = self.browse(set(get_real_ids(self.ids)))
        return super(OFPlanningIntervention, records).export_data(fields_to_export, raw_data)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'date' in groupby:
            raise UserError(_('Group by date is not supported, use the calendar view instead.'))
        return super(OFPlanningIntervention, self.with_context(virtual_id=False)).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        u""" Renvois les valeurs de champs calculées pour les RDV récurrents """
        if not self.user_has_groups('of_planning_recurring.of_group_planning_intervention_recurring'):
            return super(OFPlanningIntervention, self).read(fields=fields, load=load)

        fields2 = fields and fields[:] or []
        # Si fields2 est vide, read doit lire tous les champs, on ne veut pas ajouter 'duree' à fields2
        # Car si on l'ajoute, seul le champ duree sera lu au lieu de tous les champs
        if fields2 and 'duree' not in fields2:
            fields2.append('duree')
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        select = {x: calendar_id2real_id(x) for x in self.ids}
        real_events = self.browse(select.values())
        real_data = super(OFPlanningIntervention, real_events).read(fields=fields2, load=load)
        real_data = {d['id']: d for d in real_data}

        result = []
        for calendar_id, real_id in select.iteritems():
            if calendar_id == real_id:
                result.append(real_data[real_id])
                continue
            res = real_data[real_id].copy()
            ls = calendar_id2real_id(
                calendar_id, with_date=res and res.get('duree', 0) > 0 and res.get('duree') or 1)
            if not isinstance(ls, (basestring, int, long)) and len(ls) >= 2:
                res['date_prompt'] = ls[1]
                res['date_deadline_prompt'] = ls[2]
                # mettre en date locale pour éviter les erreurs de date pour les RDV tard le soir
                debut_dt = tz.localize(datetime.strptime(ls[1], "%Y-%m-%d %H:%M:%S"))
                res['jour'] = debut_dt.strftime("%A").capitalize()
                fin_dt = tz.localize(datetime.strptime(ls[2], "%Y-%m-%d %H:%M:%S"))
                res['jour_fin'] = fin_dt.strftime("%A").capitalize()
                res['date_deadline_forcee'] = ls[2]
                # Normalement forcer_dates vaut déjà True dans le planning récurrent de base
                # Cette surcharge ne devrait donc pas être utile
                res['forcer_dates'] = True

            res['id'] = calendar_id
            result.append(res)

        if 'duree' not in fields:
            for r in result:
                if 'duree' in r:
                    del r['duree']
        return result

    @api.multi
    def unlink(self, can_be_deleted=True):
        if not self.user_has_groups('of_planning_recurring.of_group_planning_intervention_recurring'):
            return super(OFPlanningIntervention, self).unlink()
        records_to_exclude = self.env['of.planning.intervention']
        records_to_unlink = self.env['of.planning.intervention']

        for meeting in self:
            if can_be_deleted and not is_calendar_id(meeting.id):  # if  ID REAL
                if meeting.recurrent_id:
                    # ne pas supprimer les enregistrements détachés d'un RDV récurrent
                    # pour conserver l'information de l'occurrence à sauter
                    records_to_exclude |= meeting
                else:
                    # int() required because 'id' from calendar view is a string, since it can be calendar virtual id
                    records_to_unlink |= self.browse(int(meeting.id))
            else:
                records_to_exclude |= meeting

        result = False
        if records_to_unlink:
            result = super(OFPlanningIntervention, records_to_unlink).unlink()
        if records_to_exclude:
            result = records_to_exclude.with_context(dont_notify=True).write({'active': False})
        return result

    def get_date_start_fields(self):
        return ['date', 'date_prompt', 'date_date']

    def get_date_stop_fields(self):
        return ['date_deadline', 'date_deadline_prompt', 'date_deadline_forcee']

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        if not self.user_has_groups('of_planning_recurring.of_group_planning_intervention_recurring'):
            return super(OFPlanningIntervention, self).search(
                args, offset=offset, limit=limit, order=order, count=count)
        new_args = []
        date_stop_fields = self.get_date_stop_fields()
        for arg in args:
            new_arg = arg
            # Chercher aussi les RDVs récurrents qui termine après la date donnée
            # pour pouvoir les afficher quand même si on n'affiche pas les différentes occurences
            if arg[0] in date_stop_fields and arg[1] in ('>', '>='):
                if self._context.get('virtual_id', True):
                    new_args += ['|', '&', ('recurrency', '=', 1), ('final_date', arg[1], arg[2])]
            elif arg[0] == "id":
                new_arg = (arg[0], arg[1], get_real_ids(arg[2]))
            new_args.append(new_arg)

        date_start_fields = self.get_date_start_fields()
        has_date_start_arg = any(arg[0] in date_start_fields for arg in args)
        if has_date_start_arg and not any(arg[0] in (date_stop_fields + ['final_date']) for arg in args):
            # domain with a start filter but with no stop clause should be extended
            # e.g. start=2017-01-01, count=5 => virtual occurences must be included in ('start', '>', '2017-01-02')
            start_args = new_args
            new_args = []
            for arg in start_args:
                new_arg = arg
                if arg[0] in date_start_fields:
                    new_args += ['|', '&', ('recurrency', '=', 1), ('final_date', arg[1], arg[2])]
                new_args.append(new_arg)

        # le comportement par défaut est de ne pas sélectionner les occurrences virtuelles
        if not self._context.get('virtual_id', False):
            return super(OFPlanningIntervention, self).search(
                new_args, offset=offset, limit=limit, order=order, count=count)

        if has_date_start_arg and any(arg[0] in date_stop_fields for arg in args):
            # On a une borne de début et une borne de fin, on peut se risquer à mettre une limite à 0.
            # On est à priori en vue calendar ou planning. Si on est en vue liste et que les bornes sont éloignées,
            # l'utilisateur pourra s'attendre à avoir des lenteurs
            virtual_limit = 0
            virtual_offset = 0
        else:
            virtual_limit = limit
            virtual_offset = offset

        # offset, limit, order and count must be treated separately as we may need to deal with virtual ids
        prev_events = super(OFPlanningIntervention, self).search(
            new_args, offset=virtual_offset, limit=virtual_limit, order=None, count=False)
        # ici sont virtualisés les events et ajoutés aux résultats
        events = self.browse(prev_events.get_recurrent_ids(new_args, order=order))
        if count:
            return len(events)
        elif limit:
            return events[offset: offset + limit]
        return events

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        return super(OFPlanningIntervention, self.browse(calendar_id2real_id(self.id))).copy(default)

    @api.model
    def get_recompute_tournee_fields(self):
        res = super(OFPlanningIntervention, self).get_recompute_tournee_fields()
        res.append('rrule')
        return res

    @api.multi
    def get_date_tournees(self):
        self.ensure_one()
        if self.recurrency:
            datetime_couples = self._get_recurrent_dates_by_event()
            all_dates = []
            # pour chaque occurrence
            for dt_tup in datetime_couples:
                deb_str = fields.Date.to_string(dt_tup[0])
                fin_str = fields.Date.to_string(dt_tup[1])
                all_dates.append(deb_str)
                # RDV sur plusieurs jours
                if deb_str != fin_str:
                    current_da = fields.Date.from_string(deb_str) + timedelta(days=1)
                    fin_da = fields.Date.from_string(fin_str)
                    while current_da <= fin_da:
                        all_dates.append(fields.Date.to_string(current_da))
                        current_da += timedelta(days=1)
            return all_dates
        return super(OFPlanningIntervention, self).get_date_tournees()

    # ACTIONS

    @api.multi
    def action_edit_recurrency(self):
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        # self.date is the start date of the recurence, not the calculated date of this occurence
        date_utc_dt = pytz.utc.localize(fields.Datetime.from_string(self.date))
        date_local_dt = date_utc_dt.astimezone(tz)
        date_deadline_utc_dt = pytz.utc.localize(fields.Datetime.from_string(self.date_deadline))
        date_deadline_local_dt = date_deadline_utc_dt.astimezone(tz)

        create_vals = {
            'interv_origin_id': calendar_id2real_id(self.id),
            'employee_ids': [(6, 0, self.employee_ids.ids)],
            'rec_start_date': self.date,
            'all_day': self.all_day,
            'start_hour': heures_minutes_2_float(date_local_dt.hour, date_local_dt.minute),
            'end_hour': heures_minutes_2_float(date_deadline_local_dt.hour, date_deadline_local_dt.minute),
        }
        create_vals['duration'] = create_vals['end_hour'] - create_vals['start_hour']
        if self.recurrency:
            # veut dire implicitement que le RDV existe déjà en DB et donc on peut read
            data = self.read(['date_prompt', 'date_deadline_prompt', 'rrule'])[0]
            create_vals['date'] = data.get('date_prompt')
            create_vals['date_deadline'] = data.get('date_deadline_prompt')
            create_vals['date_occurence'] = data.get('date_prompt')
            create_vals['occurence_id_str'] = self.id
        else:
            create_vals['date'] = self.date_prompt
            create_vals['date_deadline'] = self.date_deadline_prompt
            create_vals['date_occurence'] = self.date_prompt

        for field_name in self._get_recurrent_fields():
            create_vals[field_name] = self[field_name]
        # on force recurrency à True : si elle est déjà True c'est qu'on veut modifier les règles de récurrence
        # sinon c'est qu'on veut créer des règles de récurrence
        create_vals['recurrency'] = True

        wizard = self.env['of.update.rec.rules.wizard'].create(create_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': u"Modifier la récurrence",
            'res_model': 'of.update.rec.rules.wizard',
            'view_type': 'form',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # AUTRES

    @api.multi
    def get_recurrent_ids(self, domain, order=None):
        u""" Gives virtual event ids for recurring events. This method gives ids of dates
            that comes between start date and end date of calendar views
            :param order:   The fields (comma separated, format "FIELD {DESC|ASC}") on which
                            the events should be sorted
        """
        if order:
            order_fields = [field.split()[0] for field in order.split(',')]
        else:
            # fallback on self._order defined on the model
            order_fields = [field.split()[0] for field in self._order.split(',')]

        if 'id' not in order_fields:
            order_fields.append('id')

        result_data = []
        result = []
        for meeting in self:
            if not meeting.recurrency or not meeting.rrule:
                result.append(meeting.id)
                result_data.append(meeting.get_search_fields(order_fields))
                continue
            rdates = meeting._get_recurrent_dates_by_event()

            for r_start_date, r_stop_date in rdates:
                # fix domain evaluation
                # step 1: check date and replace expression by True or False, replace other expressions by True
                # step 2: evaluation of & and |
                # check if there are one False
                pile = []
                ok = True
                r_date = r_start_date  # default for empty domain
                for arg in domain:
                    if str(arg[0]) in (
                            'date', 'date_prompt', 'date_date', 'date_deadline', 'date_deadline_prompt',
                            'date_deadline_forcee', 'final_date'):
                        if str(arg[0]) in ('date', 'date_prompt', 'date_date'):
                            r_date = r_start_date
                        else:
                            r_date = r_stop_date
                        if arg[2] and len(arg[2]) > len(r_date.strftime(DEFAULT_SERVER_DATE_FORMAT)):
                            dformat = DEFAULT_SERVER_DATETIME_FORMAT
                        else:
                            dformat = DEFAULT_SERVER_DATE_FORMAT
                        if arg[1] == '=':
                            ok = r_date.strftime(dformat) == arg[2]
                        if arg[1] == '>':
                            ok = r_date.strftime(dformat) > arg[2]
                        if arg[1] == '<':
                            ok = r_date.strftime(dformat) < arg[2]
                        if arg[1] == '>=':
                            ok = r_date.strftime(dformat) >= arg[2]
                        if arg[1] == '<=':
                            ok = r_date.strftime(dformat) <= arg[2]
                        if arg[1] == '!=':
                            ok = r_date.strftime(dformat) != arg[2]
                        pile.append(ok)
                    elif str(arg) == str('&') or str(arg) == str('|'):
                        pile.append(arg)
                    else:
                        pile.append(True)
                pile.reverse()
                new_pile = []
                for item in pile:
                    if not isinstance(item, basestring):
                        res = item
                    elif str(item) == str('&'):
                        first = new_pile.pop()
                        second = new_pile.pop()
                        res = first and second
                    elif str(item) == str('|'):
                        first = new_pile.pop()
                        second = new_pile.pop()
                        res = first or second
                    new_pile.append(res)

                if [True for item in new_pile if not item]:
                    continue
                result_data.append(meeting.get_search_fields(order_fields, r_date=r_start_date))

        ids = []
        if order_fields:
            uniq = lambda it: collections.OrderedDict((id(x), x) for x in it).values()

            def comparer(left, right):
                for fn, mult in comparers:
                    result = cmp(fn(left), fn(right))
                    if result:
                        return mult * result
                return 0

            sort_params = [key.split()[0] if key[-4:].lower() != 'desc' else '-%s' % key.split()[0] for key in
                           (order or self._order).split(',')]
            sort_params = uniq(
                [comp if comp not in ['date', 'date_date', 'date_prompt'] else 'sort_start' for comp in
                 sort_params])
            sort_params = uniq(
                [comp if comp not in ['-date', '-date_date', '-date_prompt'] else '-sort_start' for comp in
                 sort_params])
            comparers = [((itemgetter(col[1:]), -1) if col[0] == '-' else (itemgetter(col), 1)) for col in sort_params]
            ids = [r['id'] for r in sorted(result_data, cmp=comparer)]

        return ids

    @api.multi
    def get_search_fields(self, order_fields, r_date=None):
        sort_fields = {}
        for field in order_fields:
            if field == 'id' and r_date:
                sort_fields[field] = real_id2calendar_id(self.id, r_date)
            else:
                sort_fields[field] = self[field]
                if isinstance(self[field], models.BaseModel):
                    name_get = self[field].mapped('display_name')
                    sort_fields[field] = name_get and name_get[0] or ''
        if r_date:
            sort_fields['sort_start'] = r_date.strftime(VIRTUALID_DATETIME_FORMAT)
        else:
            display_start = self.date_prompt
            sort_fields['sort_start'] = display_start.replace(' ', '').replace('-', '') if display_start else False
        return sort_fields

    @api.multi
    def detach_recurring_event(self, values=None, only_one=True, occurence_id=''):
        u""" Detach a virtual recurring event by duplicating the original and change reccurent values
            :param values : dict of value to override on the detached event
            :param only_one : True if we want to just detach this one. False to detach this one and all after thise one
            :param occurence_id : id string to recognize which occurence to detach
            :return : copy of the original event
        """
        if not values:
            values = {}

        real_id = calendar_id2real_id(self.id)
        meeting_origin = self.browse(real_id)
        if occurence_id:
            self = self.browse(occurence_id)

        data = self.read(['all_day', 'date_prompt', 'date_deadline_prompt', 'rrule', 'duree'])[0]
        if data.get('rrule'):
            data.update(
                values,
                verif_dispo=False,  # inhiber la verif de chevauchement
                recurrent_id=real_id,
                recurrent_id_date=data.get('date_prompt'),
                date=data.get('date_prompt'),
            )
            # si on a choisi "modifier uniquement ce RDV"
            if only_one:
                data.update(
                    rrule_type=False,
                    rrule='',
                    recurrency=False,
                    final_date=datetime.strptime(
                        data.get('date_prompt'),
                        DEFAULT_SERVER_DATETIME_FORMAT if data['all_day'] else DEFAULT_SERVER_DATETIME_FORMAT
                    ) + timedelta(hours=values.get('duree', False) or data.get('duree'))
                )

            # forcer les dates pour éviter une erreur due aux horaires
            if data.get('date_deadline_prompt'):
                data['forcer_dates'] = True
                data['date_deadline_forcee'] = data['date_deadline_prompt']
                del data['date_deadline_prompt']

            # do not copy the id
            if data.get('id'):
                del data['id']
            detached_meeting = meeting_origin.copy(default=data)

            # si on a choisi "modifier ce RDV et les suivants"
            if not only_one:
                date_last_dt = fields.Datetime.from_string(data.get('date_prompt')) - timedelta(days=1)
                # passage en date pour le calcul de rrule dans _rrule_serialize
                date_last_str = fields.Date.to_string(date_last_dt)
                if meeting_origin.end_type == 'count':
                    # réduire le compteur du RDV détaché
                    count_before_this = self.search_count([('id', '=', real_id), ('date_prompt', '<=', date_last_str)])
                    detached_meeting.count = detached_meeting.count - count_before_this
                # arrêter la récurrence du RDV d'origine
                new_rec_vals = {'end_type': 'end_date', 'final_date': date_last_str}
                new_rrule = meeting_origin._rrule_serialize(new_rec_vals)
                # une interaction étrange entre les fonctions compute et inverse fait qu'on est obligé d'inclure
                # rrule ainsi que ses champs de dépendance end_type et final_date
                # de nombreuses heures de debugging ont données lieu à ce contournement, à manipuler avec précaution
                new_rec_vals['rrule'] = new_rrule
                meeting_origin.write(new_rec_vals)
            return detached_meeting
