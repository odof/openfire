# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# 1: imports of python lib
import pytz
from datetime import timedelta
from dateutil.relativedelta import relativedelta
# 2:  imports of odoo
from odoo import api, models, fields
# 3:  imports from odoo modules
from odoo.tools.float_utils import float_compare
from odoo.addons.of_utils.models.of_utils import intersect_couple, arrondi_sup
# 4: local imports
# 5: Import of unknown third party lib

SEARCH_MODES = [
    ('distance', u"Distance (km)"),
    ('duree', u"Durée (min)"),
]


class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    website_creneaux_ids = fields.One2many(
        string=u"Créneaux site web", comodel_name='of.tournee.rdv.line.website', inverse_name='wizard_id')

    def build_website_creneaux(self, mode='day'):
        u"""Construit les créneaux affichés dans le site web, appelée depuis le controller"""
        def format_date(date):
            return fields.Date.from_string(date).strftime('%A %d %B').capitalize()
        self.ensure_one()
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        fin_matinee_flo = 13.0  # -> à récupérer depuis de la config en backend?
        debut_aprem_flo = 14.0  # -> à récupérer depuis de la config en backend?
        compare_precision = 5
        duree = self.tache_id.duree
        if mode == 'manual':
            segment = self.tache_id.sudo().segment_ids.convert_segments_to_list()
            if not segment:
                # pas de segment, pas de résultat
                self.website_creneaux_ids = [(5,)]
                return self.website_creneaux_ids
            # convert_segments_to_list retourne une liste, les taches n'ont toujours qu'un segment
            segment = segment[0]

        creneau_count = 0
        creneau_dict = {}
        for creneau_b in self.planning_ids.filtered(lambda c: c.disponible).\
                sorted(key=lambda c: c.employee_id.sudo().sequence):
            distance_prec = creneau_b.dist_prec or creneau_b.dist_ortho_prec
            if mode == 'day':
                # création d'un créneau site web
                if creneau_b.date not in creneau_dict:
                    creneau_dict[creneau_b.date] = {
                        'key': creneau_b.date,
                        'date': creneau_b.date,
                        'ids': [creneau_b.id],
                        'selected': False,
                        'distance_min': distance_prec,
                    }
                else:
                    creneau_dict[creneau_b.date]['ids'].append(creneau_b.id)
                if creneau_b.selected:
                    creneau_dict[creneau_b.date]['selected'] = True
                # nouveau min
                if distance_prec < creneau_dict[creneau_b.date]:
                    creneau_dict[creneau_b.date]['distance_min'] = distance_prec
            elif mode == 'half_day':
                # Des créneaux dispo chevauchent souvent l'heure de midi, il faut les ajouter aux créneaux front
                # du matin et de l'après midi si possible
                keys = []
                # il y a de la place entre le début du créneau et l'heure de fin de matinée
                if float_compare(creneau_b.date_flo, fin_matinee_flo - self.duree, compare_precision) <= 0:
                    keys.append(creneau_b.date + '-0-matin')
                # il y a de la place entre l'heure de début d'aprem et la fin du créneau
                if float_compare(creneau_b.date_flo_deadline, debut_aprem_flo + self.duree, compare_precision) >= 0:
                    keys.append(creneau_b.date + '-1-aprem')
                for key in keys:
                    if key not in creneau_dict:
                        # créer un nouveau créneau front
                        creneau_dict[key] = {
                            'key': key,
                            'date': creneau_b.date,
                            'ids': [creneau_b.id],
                            'selected': False,
                            'distance_min': distance_prec,
                        }
                    else:
                        creneau_dict[key]['ids'].append(creneau_b.id)
                    if creneau_b.selected:
                        creneau_dict[key]['selected'] = True
                    # nouveau min
                    if distance_prec < creneau_dict[key]:
                        creneau_dict[key]['distance_min'] = distance_prec
            elif mode == 'manual':
                keys = []
                creneaux_tache = segment[2]
                day_int = fields.Date.from_string(creneau_b.date).isoweekday()
                if day_int not in creneaux_tache:
                    continue
                creneaux_day = creneaux_tache[day_int]
                # On démarre avec des dates naïves, on doit leurs donner la tz pour comparer aux créneaux de la tâche
                tz = pytz.timezone(creneau_b.employee_id.sudo().of_tz or "Europe/Paris")
                debut_naive = fields.Datetime.from_string(creneau_b.debut_dt)
                debut = pytz.utc.localize(debut_naive)
                debut_tz = debut.astimezone(tz)
                fin_naive = fields.Datetime.from_string(creneau_b.fin_dt)
                fin = pytz.utc.localize(fin_naive)
                fin_tz = fin.astimezone(tz)
                tz_difference = debut_tz.utcoffset().seconds / 3600
                # on récupère les différents créneaux disponibles en fonction des couples (heure_debut, heure_fin)
                # en comparant les créneaux de l'employé et de la tâche
                hours_available = []
                for hour_couple in creneaux_day:
                    minute_start = debut_tz.minute and arrondi_sup(debut_tz.minute, 5) / 60.0 or 0.0
                    minute_end = fin_tz.minute and arrondi_sup(fin_tz.minute, 5) / 60.0 or 0.0
                    hour_start = float(debut_tz.hour) + minute_start
                    hour_end = float(fin_tz.hour) + minute_end
                    hours = intersect_couple(hour_couple1=hour_couple, hour_couple2=(hour_start, hour_end))
                    if hours[0] or hours[1]:
                        hours_available.append(hours)
                # On trouve des créneaux, on tente de créer des créneaux web en fonction des heures dispo et de la
                # durée de la tâche.
                for hour_min, hour_max in hours_available:
                    i = 0
                    hours = hour_max - hour_min
                    amount = int(hours / duree)
                    # on peut faire jusqu'à [amount] créneaux, on tourne jusqu'à avoir tout créé
                    while i < amount:
                        key = creneau_b.date + '-%05d' % creneau_count
                        if key not in creneau_dict:
                            start = hour_min + i * duree
                            end = hour_min + (i + 1) * duree
                            hour_start_td = timedelta(hours=start)
                            hour_start_str_li = str(hour_start_td).split(':')
                            hour_end_str_li = str(timedelta(hours=end)).split(':')
                            creneau_dict[key] = {
                                'key': key,
                                'date': creneau_b.date,
                                'ids': [creneau_b.id],
                                'selected': False,
                                'distance_min': distance_prec,
                                'description': u"%sh%s - %sh%s" % (hour_start_str_li[0], hour_start_str_li[1],
                                                                   hour_end_str_li[0], hour_end_str_li[1]),
                                'date_start': fields.Datetime.from_string(creneau_b.date) +
                                              relativedelta(hour=int(hour_start_td.seconds / 3600 - tz_difference),
                                                            minute=int(hour_start_td.seconds % 3600 / 60)),
                            }
                        if creneau_b.selected:
                            creneau_dict[key]['selected'] = True
                        if distance_prec < creneau_dict[key]:
                            creneau_dict[key]['distance_min'] = distance_prec
                        i += 1
                        creneau_count += 1

        update_vals = [(5,)]
        for k in creneau_dict:
            creneau = creneau_dict[k]
            vals = {}
            vals['key'] = creneau['key']
            vals['name'] = format_date(k)
            if mode == 'half_day':
                if k.endswith('matin'):
                    vals['description'] = u"Matin"
                else:
                    vals['description'] = u"Après-midi"
            elif mode == 'manual':
                vals['description'] = creneau['description']
                vals['date_start'] = creneau['date_start']
            vals['date'] = creneau['date']
            vals['distance_prec'] = creneau['distance_min']
            # if creneau['distance_min'] == 0:
            #     vals['description'] = u"À moins d'1km du RDV précédent"
            # else:
            #     vals['description'] = u"À %dkm du RDV précédent" % creneau['distance_min']
            vals['selected'] = creneau['selected']
            vals['planning_ids'] = [(4, id_p, 0) for id_p in creneau['ids']]
            update_vals.append((0, 0, vals))
        self.website_creneaux_ids = update_vals
        return self.website_creneaux_ids


class OFTourneeRdvLineWebsite(models.TransientModel):
    _name = 'of.tournee.rdv.line.website'
    _description = u"Créneau disponible"
    _order = 'key'

    name = fields.Char(string="Nom", default="DISPONIBLE")
    key = fields.Char(string=u"Clef")
    date = fields.Date(string="Date")
    description = fields.Text(string=u"Infos créneau", size=128)
    wizard_id = fields.Many2one('of.tournee.rdv', string="RDV", required=True, ondelete='cascade')

    planning_ids = fields.Many2many(
        string=u"Créneaux d'employés", comodel_name='of.tournee.rdv.line', relation='of_tournee_rdv_line_website_rel')
    selected = fields.Boolean(string=u"Sélectionné")
    distance_prec = fields.Float(string=u"distance min")
    date_start = fields.Datetime(
        string=u"Date de début", help=u"Ne doit être rempli qu'en granularité de réservation manuelle")

    @api.depends('name', 'key', 'date')
    def _compute_display_name(self):
        # le display_name est affiché lors de la confirmation du RDV depuis le portail
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for creneau in self:
            date_formatted = fields.Date.from_string(creneau.date).strftime('%A ' + lang.date_format)
            date_formatted = date_formatted[0].upper() + date_formatted[1:]
            if creneau.date == creneau.key:
                creneau.display_name = date_formatted
            else:
                creneau.display_name = u"%s - %s" % (date_formatted, creneau.name)

    @api.multi
    def get_closer_one(self):
        if not self:
            return False
        closer_one = self[0]
        for creneau in self[1:]:
            if creneau.distance_prec < closer_one.distance_prec:
                closer_one = creneau
        return creneau

    @api.multi
    def button_select(self, sudo=False):
        """Sélectionne ce créneau en tant que résultat. Appelée depuis le controller"""
        self.ensure_one()
        line_obj = self.env["of.tournee.rdv.line.website"]
        selected_line = line_obj.search([('wizard_id', '=', self.wizard_id.id), ('selected', '=', True)])
        selected_line.write({'selected': False})
        self.selected = True
        # sélectionner le créneau d'intervenant le plus proche au passage
        creneau_employee = self.planning_ids.sorted(lambda p: (p.dist_prec, p.dist_ortho_prec))[0]
        creneau_employee.button_select(sudo=sudo)
