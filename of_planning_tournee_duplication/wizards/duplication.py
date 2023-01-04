# -*- coding: utf-8 -*-

from odoo import api, models, fields
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo.tools.float_utils import float_compare
import pytz
# pip2.7 install holidays==0.10.4
import holidays

@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class OfDuplicationIntervention(models.TransientModel):
    _name = 'of.intervention.duplication'

    # Filtre des RDV à dupliquer - préfixe dup_
    dup_date_start = fields.Date(string=u"Date de début", required=True)
    dup_date_end = fields.Date(string=u"Date de fin", required=True)
    dup_tache_ids = fields.Many2many(
        comodel_name='of.planning.tache', string=u"Tâches",
        help=u"Si aucune tâche n'est sélectionnée, elle seront toutes prises en compte")
    # Informations des nouveaux rdv - préfixe new_
    new_date_start = fields.Date(string=u"Date de début", required=True)
    new_state = fields.Selection(
        [('draft', "Brouillon"), ('confirm', u"Confirmé")], string=u"État", required=True, default='draft')
    # autres
    line_ids = fields.One2many(
        comodel_name='of.intervention.duplication.line', inverse_name='wizard_id', string="Lignes")
    computation_done = fields.Boolean(string="Calcul fait")

    @api.multi
    def button_calculer(self):
        country = self.env.user.company_id.country_id
        days = (fields.Date.from_string(self.dup_date_end) - fields.Date.from_string(self.dup_date_start)).days
        interv_date_start = fields.Date.from_string(self.new_date_start)
        interv_date_end = interv_date_start + relativedelta(days=days)
        holi = holidays.CountryHoliday(country.code or 'FR', years=[interv_date_start.year, interv_date_end.year])
        intervention_obj = self.env['of.planning.intervention']
        domain = [
            ('date_date', '>=', self.dup_date_start),
            ('date_date', '<=', self.dup_date_end),
            ('state', 'not in', ['cancel', 'postponed']),
        ]
        if self.dup_tache_ids:
            domain += [('tache_id', 'in', [tache.id for tache in self.dup_tache_ids])]
        interventions = intervention_obj.search(domain)
        vals = {'computation_done': True}
        if interventions:
            intervs_to_duplicate = [(5, 0, 0)]
            current_date = fields.Date.from_string(self.dup_date_start)
            delta = timedelta(days=0)
            for interv in interventions:
                # increment the number of days every time we get into a new day
                interv_date = fields.Date.from_string(interv.date_date)
                if interv_date != current_date:
                    delta += timedelta(days=1)
                    current_date = interv_date
                interv_day = fields.Datetime.from_string(interv.date) + relativedelta(
                        year=interv_date_start.year,
                        month=interv_date_start.month,
                        day=interv_date_start.day,
                        days=delta.days)
                while interv_day.weekday() >= 5 or fields.Date.to_string(interv_day) in holi:
                    delta += timedelta(days=1)
                    interv_day += relativedelta(days=1)
                # Faire attention aux offset
                old_date_utc_dt = datetime.strptime(interv.date, "%Y-%m-%d %H:%M:%S")
                old_date_locale_dt = fields.Datetime.context_timestamp(interv, old_date_utc_dt)
                old_offset = old_date_locale_dt.utcoffset()
                interv_day_locale_dt = fields.Datetime.context_timestamp(interv, interv_day)
                new_offset = interv_day_locale_dt.utcoffset()
                # # récupération du offset courant
                if bool(old_offset - new_offset):  # si True = passage de UTC+2 a UTC+1 ou inverssement
                    interv_day = interv_day + old_offset - new_offset  # Datetime UTC
                intervs_to_duplicate.append((0, 0, {
                    'intervention_id': interv.id,
                    'new_date': interv_day
                }))
            vals['line_ids'] = intervs_to_duplicate
        self.update(vals)
        return {"type": "ir.actions.do_nothing"}

    @api.multi
    def button_create(self):
        tag_dup = self.env.ref('of_planning_tournee_duplication.of_planning_tournee_planning_tag_duplique',
                               raise_if_not_found=False)
        intervention_obj = self.env['of.planning.intervention']
        duplicated = 0
        alerts = 0
        no_service = 0
        rdvs = intervention_obj
        country = self.env.user.company_id.country_id
        days = (fields.Date.from_string(self.dup_date_end) - fields.Date.from_string(self.dup_date_start)).days
        interv_date_start = fields.Date.from_string(self.new_date_start)
        interv_date_end = interv_date_start + relativedelta(days=days)
        holi = holidays.CountryHoliday(country.code or 'FR', years=[interv_date_start.year, interv_date_end.year])
        for line in self.line_ids:
            if line.raison_alerte != 'none':
                alerts += 1
            rdv_vals = line.get_intervention_vals(holi)
            new_rdv = intervention_obj.new(rdv_vals)
            vals = new_rdv._convert_to_write(new_rdv._cache)
            new_interv = intervention_obj.create(vals)
            # Appeler les différents onchange désirés
            new_interv.onchange_template_id()
            # Juste créer la ligne de facturation de la tache car la durée peut être différente et bloquer la création
            # du rdv. (cas où la durée de la tache > durée du rdv provoque une alerte incohérence date)
            if new_interv.tache_id.product_id:
                values = {
                    'intervention_id': new_interv.id,
                    'product_id'     : new_interv.tache_id.product_id.id,
                    'qty'            : 1,
                    'price_unit'     : new_interv.tache_id.product_id.lst_price,
                    'name'           : new_interv.tache_id.product_id.name,
                }
                new_interv.line_ids.create(values)
            rdvs |= line.intervention_id
            duplicated += 1
            if not new_interv.service_id:
                no_service += 1
        message = u"RDV créés par duplication : %s\n" \
                  u"RDV en alerte : %s\n" \
                  u"RDV sans demande d'intervention/intervention à programmer : %s" % (duplicated, alerts, no_service)
        rdvs.write({'already_duplicated': True, 'tag_ids': [(4, tag_dup.id, 0)]})
        return self.env['of.popup.wizard'].popup_return(message=message)


class OfDupplicationInterventionLine(models.TransientModel):
    _name = 'of.intervention.duplication.line'
    _order = 'date'

    wizard_id = fields.Many2one(comodel_name='of.intervention.duplication', string="Wizard")
    intervention_id = fields.Many2one(
        comodel_name='of.planning.intervention', string="Rdv", required=True, readonly=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Partenaire", related="intervention_id.partner_id", readonly=True)
    address_id = fields.Many2one(
        comodel_name='res.partner', string="Adresse", related="intervention_id.address_id", readonly=True)
    already_duplicated = fields.Boolean(
        string=u"Déjà dupliqué", related="intervention_id.already_duplicated", readonly=True)
    date = fields.Datetime(string=u"Date dupliquée", related="intervention_id.date", readonly=True)
    duree = fields.Float(string=u"Durée", related="intervention_id.duree", readonly=True)
    forcer_dates = fields.Boolean(string=u"Forcer les dates", related="intervention_id.forcer_dates", readonly=True)
    date_deadline = fields.Datetime(
        compute="_compute_date_deadline", string="Date fin")
    new_date = fields.Datetime(string=u"Date créée")
    employee_ids = fields.Many2many(string=u"Techniciens", related="intervention_id.employee_ids", readonly=True)
    tz = fields.Selection(_tz_get, compute='_compute_tz', string="Fuseau horaire")  # vue Calendar
    raison_alerte = fields.Selection([
        ('none', ''),
        ('chevauchement', 'Chevauchement'),
        ('non_travaille', u'Horaire non travaillé'),
        ], string=u"Raison de l'alerte", compute="_compute_raison_alerte")

    @api.depends('employee_ids')
    def _compute_tz(self):
        for interv in self:
            if interv.employee_ids:
                interv.tz = interv.employee_ids[0].of_tz

    @api.depends('date', 'duree', 'employee_ids', 'forcer_dates')
    def _compute_date_deadline(self):
        """Utilise les horaires des employés pour calculer la date de fin de l'intervention"""
        compare_precision = 5
        employee_obj = self.env['hr.employee']
        for interv in self:
            if not (interv.employee_ids and interv.date and interv.duree):
                continue

            if interv.forcer_dates:
                interv.date_deadline = False
            else:
                employees = interv.employee_ids
                tz = pytz.timezone(interv.tz)
                if not tz:
                    tz = "Europe/Paris"

                # Génération courante_da
                date_utc_dt = datetime.strptime(interv.new_date, "%Y-%m-%d %H:%M:%S")  # Datetime UTC
                date_locale_dt = fields.Datetime.context_timestamp(interv, date_utc_dt)  # Datetime local
                date_locale_str = fields.Datetime.to_string(date_locale_dt).decode('utf-8')  # String Datetime local
                date_courante_da = fields.Date.from_string(date_locale_str)  # Date local
                date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')
                un_jour = timedelta(days=1)
                une_semaine = timedelta(days=7)
                # Pour des raisons pratiques on limite la recherche des horaires à une semaine après la date d'intervention
                date_stop_dt = date_locale_dt + une_semaine
                date_stop_str = fields.Datetime.to_string(date_stop_dt).decode('utf-8')
                # Récupérer le dictionnaire des segments horaires des employés
                horaires_list_dict = employees.get_horaires(date_locale_str, date_stop_str)
                # Récupérer la liste des segments de l'équipe (i.e. l'intersection des horaires des employés)
                segments_equipe = employees.get_horaires_intersection(horaires_list_dict=horaires_list_dict)

                jour_courant = date_locale_dt.isoweekday()

                duree_restante = interv.duree
                # heure en float
                heure_debut = date_locale_dt.hour + (date_locale_dt.minute + date_locale_dt.second / 60.0) / 60.0

                # Vérifier que l'intervention commence sur un créneau travaillé
                index_creneau = employee_obj.debut_sur_creneau(date_courante_str, heure_debut, segments_equipe)
                if index_creneau == -1:
                    interv.alert_hors_creneau = True
                    interv.date_deadline = False
                    continue

                heure_courante = heure_debut
                segment_courant = segments_equipe.pop(0)
                horaires_dict = segment_courant[2]
                while float_compare(duree_restante, 0.0, compare_precision) > 0.0:

                    fin_creneau_courant = horaires_dict[jour_courant][index_creneau][1]
                    if float_compare(fin_creneau_courant, heure_courante + duree_restante, compare_precision) >= 0.0:
                        # L'intervention se termine sur ce créneau
                        heure_courante += duree_restante
                        break
                    # L'intervention continue.
                    # Y-a-t-il un créneau suivant la même journée ?
                    if index_creneau + 1 < len(horaires_dict[jour_courant]):  # oui
                        duree_restante -= (horaires_dict[jour_courant][index_creneau][1] - heure_courante)
                        index_creneau += 1
                        heure_courante = horaires_dict[jour_courant][index_creneau][0]
                        continue
                    # Il n'y a pas de créneau suivant la même journée : terminer la journée puis passer au jour suivant.
                    duree_restante -= (horaires_dict[jour_courant][index_creneau][1] - heure_courante)

                    jour_courant = ((jour_courant + 1) % 7) or 7  # num jour de la semaine entre 1 et 7
                    date_courante_da += un_jour
                    date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')

                    if date_courante_str > segment_courant[1] and len(segments_equipe) > 0:
                        # Changer de segment courant
                        segment_courant = segments_equipe.pop(0)
                        horaires_dict = segment_courant[2]

                    while jour_courant not in horaires_dict or horaires_dict[jour_courant] == []:
                        # On saute les jours non travaillés.
                        jour_courant = ((jour_courant + 1) % 7) or 7  # num jour de la semaine entre 1 et 7
                        date_courante_da += un_jour
                        if date_courante_str > segment_courant[1] and len(segments_equipe) > 0:
                            # Changer de segment courant
                            segment_courant = segments_equipe.pop(0)
                            horaires_dict = segment_courant[2]

                    index_creneau = 0
                    # Heure_courante passée à l'heure de début du premier créneau du jour travaillé suivant
                    heure_courante = horaires_dict[jour_courant][index_creneau][0]

                # La durée restante est égale à 0 ! on y est !
                # String date courante locale
                date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')
                # Datetime local début du jour
                date_courante_deb_dt = tz.localize(datetime.strptime(date_courante_str, "%Y-%m-%d"))
                # Calcul de la nouvelle date
                date_deadline_locale_dt = date_courante_deb_dt + timedelta(hours=heure_courante)
                # Conversion en UTC
                date_deadline_utc_dt = date_deadline_locale_dt - date_deadline_locale_dt.tzinfo._utcoffset
                date_deadline_str = date_deadline_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                interv.date_deadline = date_deadline_str

    @api.depends('new_date')
    def _compute_raison_alerte(self):
        interv_obj = self.env['of.planning.intervention']
        employee_obj = self.env['hr.employee']
        for line in self:
            date = fields.Datetime.from_string(line.new_date)
            deadline = date + relativedelta(hours=line.intervention_id.duree)
            # recherche provenant de of.planning.intervention.do_verif_dispo()
            # adaptée pour utiliser les dates des rdv à créer
            rdv = interv_obj.search([
                ('employee_ids', 'in', line.employee_ids.ids),
                ('date', '<', fields.Datetime.to_string(deadline)),
                ('date_deadline', '>', line.new_date),
                ('state', 'not in', ('cancel', 'postponed')),
                ], limit=1)
            if rdv:
                line.raison_alerte = 'chevauchement'
                continue

            # Segment de code repris de of.planning.intervention._compute_date_deadline()
            # Sert a vérifier si l'intervention est dans les horaires de l'employé
            date_utc_dt = datetime.strptime(line.new_date, "%Y-%m-%d %H:%M:%S")  # Datetime UTC
            date_fin_utc_dt = False
            if line.date_deadline:
                date_fin_utc_dt = datetime.strptime(line.date_deadline, "%Y-%m-%d %H:%M:%S")  # Datetime UTC
            elif line.forcer_dates:
                date_fin_utc_dt = date_utc_dt + relativedelta(minutes=line.duree)
            date_locale_dt = fields.Datetime.context_timestamp(line, date_utc_dt)  # Datetime local
            date_locale_str = fields.Datetime.to_string(date_locale_dt).decode('utf-8')  # String Datetime local
            date_courante_da = fields.Date.from_string(date_locale_str)  # Date local
            date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')
            date_stop_dt = date_locale_dt + timedelta(days=7)
            date_stop_str = fields.Datetime.to_string(date_stop_dt).decode('utf-8')
            horaires_list_dict = line.employee_ids.get_horaires(date_locale_str, date_stop_str)
            # Récupérer la liste des segments de l'équipe (i.e. l'intersection des horaires des employés)
            segments_equipe = line.employee_ids.get_horaires_intersection(horaires_list_dict=horaires_list_dict)
            # heure en float
            heure_debut = date_locale_dt.hour + (date_locale_dt.minute + date_locale_dt.second / 60.0) / 60.0
            heure_fin = 0
            if date_fin_utc_dt:
                date_fin_locale_dt = fields.Datetime.context_timestamp(line, date_fin_utc_dt)
                heure_fin = date_fin_locale_dt.hour + (date_fin_locale_dt.minute + date_fin_locale_dt.second / 60.0) / 60.0
                # hack pour debut_sur_creneau, la vérification étant la suivante heure_début <= heure_testée < heure_fin
                # si heure_testée = heure_fin alors renvoi -1. Pour l'heure de fin on fait donc heure_testée-0.01
                heure_fin -= 0.01
            # Vérifier que l'intervention commence sur un créneau travaillé
            index_creneau_deb = employee_obj.debut_sur_creneau(date_courante_str, heure_debut, segments_equipe)
            index_creneau_fin = employee_obj.debut_sur_creneau(date_courante_str,
                                                               heure_fin or heure_debut + line.intervention_id.duree,
                                                               segments_equipe)
            if index_creneau_deb == -1 or index_creneau_fin == -1:
                line.raison_alerte = 'non_travaille'
                continue
            line.raison_alerte = 'none'

    @api.multi
    def get_intervention_vals(self, holi=[]):
        self.ensure_one()
        tag_create_dup = self.env.ref(
            'of_planning_tournee_duplication.of_planning_tournee_planning_tag_cree_par_duplication',
            raise_if_not_found=False)
        tag_alert_dup = self.env.ref(
            'of_planning_tournee_duplication.of_planning_tournee_planning_tag_alerte_duplication',
            raise_if_not_found=False)
        rdv_vals = self.intervention_id.copy_data()[0]
        # On ne conserve pas la commande.
        if 'order_id' in rdv_vals:
            del rdv_vals['order_id']
        # On ne conserve pas le BL.
            if 'picking_id' in rdv_vals:
                del rdv_vals['picking_id']
        rdv_vals['verif_dispo'] = False
        # rdv_vals['employee_ids'] = [(4, self.employee_id.id, 0)]
        date_origine = rdv_vals['date']
        rdv_vals['date'] = self.new_date
        rdv_vals['state'] = self.wizard_id.new_state
        rdv_vals['is_duplication'] = True
        if 'service_id' in rdv_vals:
            del rdv_vals['service_id']
        # si le rdv d'origine a le champ forcer_dates = True ou l'alerte 'non_travaill'
        # alors on doit également calculer la date de fin forcée
        if rdv_vals.get('forcer_dates', False) or self.raison_alerte == 'non_travaille':
            rdv_vals['forcer_dates'] = True
            date_deadline_forcee = rdv_vals.get('date_deadline_forcee', False)
            ds = fields.Datetime.from_string(self.new_date)
            new_offset = fields.Datetime.context_timestamp(self, ds).utcoffset()
            if date_deadline_forcee:
                ddf = fields.Datetime.from_string(date_deadline_forcee)
                ori = fields.Datetime.from_string(date_origine)
                old_offset = fields.Datetime.context_timestamp(self, ori).utcoffset()
                # Le RDV peut être sur 2 jours mais comme il commence un vendredi alors il fait 4 jours au lieu de 2.
                # On retire donc les jours qui ne devraient pas être présents
                days_to_end = (ddf - ori).days
                current_interv_day = datetime(year=ori.year, month=ori.month, day=ori.day)
                while current_interv_day < ddf:
                    if current_interv_day.weekday() >= 5 or fields.Date.to_string(current_interv_day) in holi:
                        days_to_end -= 1
                    current_interv_day += relativedelta(days=1)
                new_ddf = ds + relativedelta(days=days_to_end, hour=ddf.hour, minute=ddf.minute, second=ddf.second)
                if bool(old_offset - new_offset):  # si True = passage de UTC+2 a UTC+1 ou inverssement
                    new_ddf = new_ddf + old_offset - new_offset
            else:
                new_ddf = ds + relativedelta(hours=rdv_vals['duree'])
            # Une fois calculée, c'est possible que certains jours soient sur WE ou jours fériés.
            # Si c'est le cas on doit changer la date de fin
            counter = (new_ddf - ds).days + 1
            current_interv_day = datetime(year=ds.year, month=ds.month, day=ds.day)
            while counter > 0:
                if not current_interv_day.weekday() >= 5 and not fields.Date.to_string(current_interv_day) in holi:
                    counter -= 1
                if counter > 0:
                    current_interv_day += relativedelta(days=1)
            true_ddf = new_ddf + relativedelta(year=current_interv_day.year,
                                               month=current_interv_day.month,
                                               day=current_interv_day.day)
            rdv_vals['date_deadline_forcee'] = fields.Datetime.to_string(true_ddf)
        if tag_create_dup:
            rdv_vals['tag_ids'] = [(4, tag_create_dup.id, 0)]
        if self.raison_alerte != 'none' and tag_alert_dup:
            rdv_vals['tag_ids'].append((4, tag_alert_dup.id, 0))
        return rdv_vals
