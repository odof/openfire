# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.addons.of_utils.models.of_utils import se_chevauchent, format_date, hours_to_strs
from odoo.tools.float_utils import float_compare
from datetime import datetime, timedelta, date
from odoo.addons.of_geolocalize.models.of_geo import GEO_PRECISION
import pytz
import holidays
from copy import deepcopy


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class HREmployee(models.Model):
    _inherit = "hr.employee"
    _order = "sequence"

    # Defaults

    @api.model
    def default_get(self, fields=None):
        res = super(HREmployee, self).default_get(fields)
        res['of_tz'] = self.env.user.tz or 'Europe/Paris'
        return res

    # Champs

    # Onglet "Informations publiques"
    of_address_depart_id = fields.Many2one('res.partner', string=u'Adresse de départ')
    of_address_retour_id = fields.Many2one('res.partner', string='Adresse de retour')
    of_color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D",
                              oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0",
                              oldname="color_bg")
    # Onglet "Horaires
    of_mode_horaires = fields.Selection([
        ("easy", "Facile"),
        ("advanced", u"Avancé")], string=u"Mode de sélection des horaires", required=True, default="easy")
    of_segment_ids = fields.One2many(
        'of.horaire.segment', 'employee_id', string="Horaires de travail", domain=[('type', '=', 'regular')])
    of_horaire_recap = fields.Html(compute='_compute_of_horaire_recap', string="Horaires de travail")
    of_tz = fields.Selection(_tz_get, string='Fuseau horaire', required=True, help=u"Le fuseau horaire de l'employé")
    of_tz_offset = fields.Char(compute='_compute_of_tz_offset', string='Timezone offset', invisible=True)

    # Autres
    sequence = fields.Integer(string=u"Séquence d'affichage", help=u"""
        Champ pour définir l'ordre d'affichage des employés. Du plus petit au plus grand.""")

    # @api.depends

    @api.depends('of_segment_ids')
    def _compute_of_horaire_recap(self):
        def format_date(date):
            return fields.Date.from_string(date).strftime(lang.date_format)

        def formate_segment(segment):
            return '<p>\n&nbsp;&nbsp;&nbsp;' + '<br/>\n&nbsp;&nbsp;&nbsp;'.join(segment.format_str_list()) + '</p>\n'

        segment_obj = self.env['of.horaire.segment']
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        date_str = self._context.get('of_horaire_recap_start') or fields.Date.today()

        for employee in self:
            segments_temp = segment_obj.search([
                ('employee_id', '=', employee.id),
                ('permanent', '=', False),
                ('date_fin', '>=', date_str),
                ('type', '=', 'regular')])
            segments_perm = segment_obj.search([
                ('employee_id', '=', employee.id),
                ('permanent', '=', True),
                ('type', '=', 'regular')], order="date_deb")

            recap = u"<p><i class='oe_grey'>Les horaires passés ne sont pas affichés.</i></p>"
            if segments_perm:
                segments_perm_futur = segments_perm.filtered(lambda s: s.date_deb > date_str)
                segments_perm_passe = (segments_perm - segments_perm_futur)
                if segments_perm_passe:
                    segment_perm_cur = segments_perm_passe[-1]

                    if segment_perm_cur.date_deb != "1970-01-01":
                        depuis_cur = u"le " + format_date(segment_perm_cur.date_deb)
                    else:
                        depuis_cur = u"l'embauche"
                    if segment_perm_cur.motif:
                        depuis_cur += u"(%s)" % segment_perm_cur.motif

                    recap += u'<h3>Horaires depuis %s</h3>\n<p>\n%s</p>\n' % (depuis_cur, formate_segment(segment_perm_cur))

                for seg in segments_perm_futur:
                    recap += u"<h3>Horaires à partir du " + format_date(seg.date_deb)
                    if seg.motif:
                        recap += u" (%s)" % seg.motif
                    recap += u'</h3>\n<p>\n' + formate_segment(seg) + u'</p>\n'
            else:
                recap = u"<p><b class='of_red'><i class='fa fa-lg fa-warning'/> Aucun horaire permanent n'est renseigné</b></p>"
            if segments_temp:
                recap += u"<h3>Horaires temporaires à venir</h3>\n"
                for seg in segments_temp:
                    if seg.date_deb == seg.date_fin:
                        recap += u"<h5>Le " + format_date(seg.date_deb)
                    else:
                        recap += u"<h5>du %s au %s" % (format_date(seg.date_deb),
                                                       format_date(seg.date_fin))
                    if seg.motif:
                        recap += u" (%s)" % seg.motif
                    recap += u'</h5>\n<p>\n' + formate_segment(seg) + u'</p>\n'
            employee.of_horaire_recap = recap

    @api.depends('of_tz')
    def _compute_of_tz_offset(self):
        for employee in self:
            employee.of_tz_offset = datetime.now(pytz.timezone(employee.of_tz or 'GMT')).strftime('%z')

    # @api.onchange

    @api.onchange('user_id')
    def _onchange_user_id(self):
        self.ensure_one()
        if self.user_id:
            self.of_tz = self.user_id.tz
            self.of_color_ft = self.user_id.of_color_ft
            self.of_color_bg = self.user_id.of_color_bg

    @api.onchange('of_address_depart_id')
    def _onchange_address_depart_id(self):
        self.ensure_one()
        if self.of_address_depart_id:
            self.of_address_retour_id = self.of_address_depart_id

    # Héritages

    @api.multi
    def write(self, vals):
        res = super(HREmployee, self).write(vals)
        user_ids = self.mapped('user_id')
        if vals.get("of_color_ft", False) and not vals.get("no_rebounce", False):
            user_ids.write({'of_color_ft': vals.get("of_color_ft", False), 'no_rebounce': True})
        if vals.get("of_color_bg", False) and not vals.get("no_rebounce", False):
            user_ids.write({'of_color_bg': vals.get("of_color_bg", False), 'no_rebounce': True})
        return res

    @api.model
    def create(self, vals):
        employee = super(HREmployee, self).create(vals)
        if employee.user_id:
            if vals.get("of_color_ft", False) and not vals.get("no_rebounce", False):
                employee.user_id.write({'of_color_ft': vals.get("of_color_ft", False), 'no_rebounce': True})
            if vals.get("of_color_bg", False) and not vals.get("no_rebounce", False):
                employee.user_id.write({'of_color_bg': vals.get("of_color_bg", False), 'no_rebounce': True})
        return employee

    # Autres méthodes

    @api.multi
    def convert_segments_to_list(self, segments=False):
        result = []
        for segment in segments or self.of_segment_ids:
            creneaux_dict = {i+1: [] for i in xrange(7)}
            for creneau in segment.creneau_ids:
                creneaux_dict[creneau.jour_number].append([creneau.heure_debut, creneau.heure_fin])
            result.append([segment.date_deb, segment.date_fin, creneaux_dict])
        return result

    @api.multi
    def get_archive_list_segments(self):
        """Renvoie l'archive des horaires des employés sous forme de liste
        @TODO : Supprimer cette fonction et optimiser les fonctions qui l'appellent.
        :return: Liste des horaires pour chaque employé
        :rtype: dict {  employee_id :  [ [date_debut, date_fin, horaires_dict], ...],  ...  }"""
        return {
            employee.id: employee.convert_segments_to_list(employee.of_segment_ids.filtered('permanent'))
            for employee in self
        }

    @api.multi
    def get_archive_list_segments_temp(self):
        """Renvoie l'archive des horaires des employés sous forme de liste
        @TODO: Supprimer cette fonction et optimiser les fonctions qui l'appellent.
        :return: Liste des horaires pour chaque employé
        :rtype: dict {  employee_id :  [ [date_debut, date_fin, horaires_dict], ...],  ...  }"""
        return {
            employee.id: employee.convert_segments_to_list(employee.of_segment_ids.filtered(lambda e: not e.permanent))
            for employee in self
        }

    @api.multi
    def get_horaires_date(self, date_param, response_text=False, seg_type='regular'):
        """Renvoie les horaires des employés à la date donnée en paramètre.
        :param date_param: date d'évaluation au format string ou Date
        :param response_text: True si on veut le résultat sous forme de chaine de caractères
        :param seg_type: Type d'horaire
        :rtype: { employee_id :  [(h_deb, h_fin), (h_deb, h_fin), ..] ,  .. }"""
        segment_obj = self.env['of.horaire.segment']
        # init date_str et date_da en fonction de date_param
        if isinstance(date_param, basestring):
            date_da = fields.Date.from_string(date_param)
            date_str = date_param
        else:
            date_da = date_param
            date_str = fields.Date.to_string(date_param)
        if not date_da:  # sur création depuis vue liste, date peut être None
            if response_text:
                return u""
            else:
                return {employee.id: [] for employee in self}
        num_jour = date_da.isoweekday()  # entre 1 et 7
        res = {}
        res_text = u""
        for employee in self:
            # Récupération du segment, si possible temporaire, avec la date de début la plus avancée
            segment = segment_obj.search([('employee_id', '=', employee.id),
                                          ('date_deb', '<=', date_str),
                                          ('date_fin', '>=', date_str),
                                          ('type', '=', seg_type)],
                                         order='permanent, date_deb desc',
                                         limit=1)
            if not segment:
                segment = segment_obj.search([('employee_id', '=', employee.id),
                                              ('date_fin', '=', False),
                                              ('type', '=', seg_type)], limit=1)
            # si même après ça il n'y a aucun segment de défini, res[employee.id] = []
            # conserver ainsi car utilisé dans le js
            creneaux = segment.creneau_ids.filtered(lambda c: c.jour_number == num_jour)
            res[employee.id] = [[creneau.heure_debut, creneau.heure_fin] for creneau in creneaux]
            if res_text:
                res_text += u"\n"
            if not creneaux:
                res_text += u"%s: Non travaillé" % employee.name
            else:
                res_text += u"%s: %s" % (employee.name, ", ".join(
                    ["%s-%s" % (
                        hours_to_strs(creneau.heure_debut)[0],
                        hours_to_strs(creneau.heure_fin)[0]) for creneau in creneaux]))
        if response_text:
            return res_text
        return res

    @api.multi
    def get_horaires(self, date_start, date_stop):
        """Renvoie les horaires des employés de self entre 2 dates
        :param date_start: date de début d'évaluation, incluse.
        :param date_stop: date de fin d'évaluation, incluse.
        :rtype: dict { employee_id :  [(date_debut, date_fin, horaires_dict), ...] ,  ... }
        """
        segment_obj = self.env['of.horaire.segment']
        if len(date_start) == 10:  # les paramètres sont des dates
            mode_params = "date"
        else:
            # transformer date_start et date_stop en date locale
            date_start_naive_dt = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")  # datetime naif
            date_start_utc_dt = pytz.utc.localize(date_start_naive_dt, is_dst=None)  # datetime utc
            date_stop_naive_dt = datetime.strptime(date_stop, "%Y-%m-%d %H:%M:%S")  # datetime naif
            date_stop_utc_dt = pytz.utc.localize(date_stop_naive_dt, is_dst=None)  # datetime utc
            mode_params = "datetime"
        un_jour = timedelta(days=1)

        res = {}
        for employee in self:
            if not employee.of_segment_ids:
                # L'employé n'a pas d'horaires définis
                res[employee.id] = []
                continue

            # En cas d'employés sur différentes timezones
            tz = pytz.timezone(employee.of_tz or "Europe/Paris")
            if mode_params == "datetime":
                date_start_local_dt = date_start_utc_dt.astimezone(tz)  # datetime local
                date_stop_local_dt = date_stop_utc_dt.astimezone(tz)  # datetime local
                date_start_str = fields.Date.to_string(date_start_local_dt).decode('utf-8')
                date_stop_str = fields.Date.to_string(date_stop_local_dt).decode('utf-8')
            else:
                date_start_str = date_start
                date_stop_str = date_stop

            segments = segment_obj.search([('employee_id', '=', employee.id), ('type', '=', 'regular'),
                                           '|', ('date_fin', '=', False), ('date_fin', '>', date_start_str),
                                           '|', ('date_deb', '=', False), ('date_deb', '<=', date_stop_str)])
            date_deb = date_start_str
            pile = []
            horaires = []
            for segment in segments + segment_obj.browse(-1):
                # A chaque itération :
                # date_deb = date à partir de laquelle il faut ajouter des éléments dans horaires
                # pile = liste des (segment, horaires_str) qui commencent avant date_deb et se terminent après
                # horaires = liste des horaires à retourner et dont la date de fin est inférieure à date_deb
                if segment.id != -1:
                    segment_deb = segment.date_deb or date_deb
                    segment_fin = segment.date_fin
                    date_fin_temp_da = fields.Date.from_string(segment_deb)
                    date_fin_temp_da -= un_jour
                    date_fin = fields.Date.to_string(date_fin_temp_da).decode('utf-8')
                else:
                    # On a fini de parcourir tous les segments, il ne reste qu'à finir de vider la pile
                    segment = False
                    date_fin = date_stop_str
                    segment_deb = segment_fin = date_stop_str + 'Z'

                while date_deb <= date_fin:
                    # Ajout des segments de la pile pour combler le vide avant la date segment_deb
                    if pile:
                        seg_prec, hor_prec = pile[-1]
                        if seg_prec.date_fin and seg_prec.date_fin <= date_fin:
                            # Le segment précédent se termine avant le début du segment en cours
                            horaires.append([date_deb, seg_prec.date_fin, hor_prec])
                            pile.pop()
                            seg_prec_date_fin_da = fields.Date.from_string(seg_prec.date_fin)
                            date_deb = fields.Date.to_string(seg_prec_date_fin_da + un_jour).decode('utf-8')
                        elif segment and segment.permanent and not seg_prec.permanent:
                            # Si le segment en cours est permanent et qu'il reste des segments temporaires non finis,
                            # ceux-cis sont prioritaires. On continue donc sans ajouter d'horaire.
                            break
                        else:
                            horaires.append([date_deb, date_fin, hor_prec])
                            date_deb = segment_deb
                    else:
                        # Aucun horaire n'a été défini sur cette période
                        # @todo: Utiliser le prochain horaire permanent ?
                        horaires.append([date_deb, date_fin, {}])
                        date_deb = segment_deb

                while pile and (pile[-1][0].date_fin or date_stop_str) <= segment_fin:
                    pile.pop()

                # Ajout du segment dans la pile
                segment_data = (segment, segment and self.convert_segments_to_list(segment)[0][2])
                if segment and segment.permanent:
                    if pile and pile[0][0].permanent:
                        # Un segment permanent en remplace un autre
                        pile[0] = segment_data
                    else:
                        pile = [segment_data] + pile
                else:
                    pile.append(segment_data)
            res[employee.id] = horaires

        # WHOO HOO on y est! \o/
        # le résultat est un dictionnaire avec les identifiants des employés en clés
        # les valeurs sont de la forme [ [debut, fin, horaires] ,  [debut, fin, horaires] ,  ... ]
        # avec un seul choix d'horaires possibles pour une date donnée
        return res

    @api.multi
    def get_horaires_intersection(self, date_start=False, date_stop=False, horaires_list_dict=False):
        """Renvoie l'intersection des horaires des employés du self
        avec soit les dates connues, soit le horaires_list_dict
        :param date_start: date de début d'évaluation, incluse.
        :param date_stop: date de fin d'évaluation, incluse.
        :param horaires_list_dict: dict horaires pour éviter de le recalculer si on le connait déjà
        :rtype: list [ (date_debut_da, date_fin_da, horaires_dict) , (date_debut_da, date_fin_da, horaires_dict) ,  ..]
        """
        res = []
        if len(self) == 0:
            return res
        if not horaires_list_dict:
            horaires_list_dict = self.get_horaires(date_start, date_stop)
        if len(self) == 1:
            res = horaires_list_dict[self.id]
            return res
        emp_1_id = self[0].id
        res = horaires_list_dict[emp_1_id]
        for emp_2_id in self.ids[1:]:
            res = self.get_intersection_segments(res, horaires_list_dict[emp_2_id])
        return res

    @api.model
    def get_intersection_segments(self, segments_emp_1, segments_emp_2):
        """Renvoie l'intersection des horaires de 2 segments
        :param segments_emp_1: 1er segment horaires à fusionner.
        :param segments_emp_2: 2ème segment horaires à fusionner.
        :rtype: list [ (date_debut_da, date_fin_da, horaires_dict) ,  (date_debut_da, date_fin_da, horaires_dict) ,  ..]
        """
        res = []
        if len(segments_emp_1) == 0 or len(segments_emp_2) == 0:
            return res
        un_jour = timedelta(days=1)
        pre_res = []
        # Fusionner les listes de segments pour que les dates correspondent,
        # en conservant les 2 horaires_dict à chaque fois
        while len(segments_emp_1) > 0 and len(segments_emp_2) > 0:
            date_fin_1_da = fields.Date.from_string(segments_emp_1[0][1])  # date de fin du premier segment de la liste
            date_fin_2_da = fields.Date.from_string(segments_emp_2[0][1])  # date de fin du premier segment de la liste

            if date_fin_1_da < date_fin_2_da:  # le premier segment de l'employé 1 termine en premier
                date_debut_2_da = date_fin_1_da + un_jour
                debut_2_str = fields.Date.to_string(date_debut_2_da)
                segments_emp_2[0][0] = debut_2_str
                segment_fuz = list(segments_emp_1.pop(0))  # conversion de tuple à list pour pouvoir ajouter un élément
                segment_fuz.append(segments_emp_2[0][2])  # ajout du horaires_dict
                pre_res.append(segment_fuz)
            elif date_fin_1_da > date_fin_2_da:  # le premier segment de l'employé 2 termine en premier
                date_debut_1_da = date_fin_2_da + un_jour
                debut_1_str = fields.Date.to_string(date_debut_1_da)
                segments_emp_1[0][0] = debut_1_str
                segment_fuz = list(segments_emp_2.pop(0))  # conversion de tuple à list pour pouvoir ajouter un élément
                segment_fuz.append(segments_emp_1[0][2])  # ajout du horaires_dict
                pre_res.append(segment_fuz)
            else:  # les premiers segments des deux employés terminent en même temps
                segment_fuz = list(segments_emp_1[0])  # conversion de tuple à list pour pouvoir ajouter un élément
                segment_fuz.append(segments_emp_2[0][2])  # ajout du horaires_dict
                pre_res.append(segment_fuz)
                segments_emp_1.pop(0)
                segments_emp_2.pop(0)
        # On a à présent une liste de segments avec 2 horaires_dict dans chaque.
        # On fusionne les horaires_dict pour garder leur intersection
        for segment in pre_res:
            segment_fuz = [segment[0], segment[1], self.get_intersection_heures_dict(segment[2], segment[3])]
            res.append(segment_fuz)
        return res

    @api.model
    def get_intersection_heures_dict(self, dict1, dict2):
        """Fusionne 2 horaires_dict et renvoie leur intersection
        exemple: dict1[1] = [(9, 12)], dict2 = [(11, 14)]; res[1] = [(11, 12)]
        :param dict1: 1er horaires_dict à fusionner.
        :param dict1: 2ème horaires_dict à fusionner.
        :rtype: dict { 1..7 :  [(h_debut, h_fin), (h_debut, h_fin)] }
        """
        res = {}
        for i in xrange(1, 8):  # parcourir les jours de la semaine
            res[i] = []
            if i not in dict1 or i not in dict2:  # l'une des 2 listes est vide: pas d'intersection
                continue
            list1 = deepcopy(dict1[i])  # liste des créneaux travaillés pour le jour i
            list2 = deepcopy(dict2[i])  # liste des créneaux travaillés pour le jour i

            while len(list1) > 0 and len(list2) > 0:
                if se_chevauchent(list1[0][0], list1[0][1], list2[0][0], list2[0][1]):  # les 2 créneaux se chevauchent!
                    # intersection des 2 créneaux
                    res[i].append((max(list1[0][0], list2[0][0]), min(list1[0][1], list2[0][1])))
                    # la nouvelle heure de début est l'heure de fin du créneau qui termine en premier
                    if list1[0][1] < list2[0][1]:  # le 1er créneau de list1 termine avant le premier créneau de list2
                        list1.pop(0)
                    elif list1[0][1] > list2[0][1]:  # le 1er créneau de list2 termine avant le premier créneau de list1
                        list2.pop(0)
                    else:
                        list1.pop(0)
                        list2.pop(0)
                else:  # les 2 créneaux ne se chevauchent pas: on retire celui qui termine en premier
                    if list1[0][1] < list2[0][1]:  # le 1er créneau de list1 termine avant le premier créneau de list2
                        list1.pop(0)
                    else:  # le 1er créneau de list2 termine avant le premier créneau de list1
                        list2.pop(0)
        return res

    @api.model
    def debut_sur_creneau(self, date_str, h_debut, list_segments):
        """Renvoie l'indexe du créneau de début si l'heure et la date sont dans les horaires, -1 sinon
        :param date_str: date d'évaluation.
        :param h_debut: heure d'évaluation.
        :param list_segments: segments horaires d'évaluation.
        """
        for segment in list_segments:
            if segment[0] <= date_str <= segment[1]:  # la date est sur ce segment
                date_da = fields.Date.from_string(date_str)
                num_jour = date_da.isoweekday()
                creneaux = segment[2].get(num_jour, False)
                if not creneaux:
                    return -1
                for i in xrange(len(creneaux)):  # creneau sous form (h_debut, h_fin)
                    creneau = creneaux[i]
                    if creneau[0] <= h_debut < creneau[1]:
                        return i
                return -1
        return -1


class OFHoraireSegment(models.Model):
    _name = 'of.horaire.segment'
    _order = 'employee_id, date_deb, permanent DESC'

    # Contraintes

    @api.constrains('creneau_ids')
    def check_no_overlapping(self):
        for segment in self:
            for creneaux in segment.creneau_ids:
                creneaux_len = len(creneaux)
                for j in xrange(creneaux_len - 1):
                    if creneaux[j].jour_id != creneaux[j + 1].jour_id:
                        continue
                    d1 = creneaux[j].heure_debut
                    f1 = creneaux[j].heure_fin
                    d2 = creneaux[j + 1].heure_debut
                    f2 = creneaux[j + 1].heure_fin
                    if se_chevauchent(d1, f1, d2, f2):
                        raise UserError(u"Oups! Des créneaux se chevauchent")

    name = fields.Char(string=u"Période", compute="_compute_name")
    type = fields.Selection(
        selection=[('regular', u"Normaux")], string=u"Type d'horaires", required=True, default='regular')
    employee_id = fields.Many2one('hr.employee', string=u"Employé", required=True, ondelete='cascade')
    date_deb = fields.Date(string=u"Date de début", default="1970-01-01")
    date_fin = fields.Date(string="Date de fin")
    permanent = fields.Boolean(
        string="Est un horaire permanent",
        help=u"Horaires valables sur une durée indéterminée."
    )
    creneau_ids = fields.Many2many(
        "of.horaire.creneau", "of_segment_creneau_rel", "segment_id", "creneau_id",
        string=u"Créneaux"
    )
    modele_id = fields.Many2one('of.horaire.modele', string=u"Charger un modèle", compute=lambda *args: None)
    active = fields.Boolean(string="Active", default=True)
    motif = fields.Char(string="Motif du changement")

    # @api.depends

    @api.multi
    @api.depends('date_deb', 'date_fin', 'permanent', 'motif')
    def _compute_name(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for segment in self:
            if segment.permanent:
                if segment.date_deb:
                    name = _(u"À partir du ") + format_date(segment.date_deb, lang)
                else:
                    name = _(u"Depuis l'embauche")
            elif segment.date_deb != segment.date_fin:
                name = _(u"Du %s au %s") % (format_date(segment.date_deb, lang), format_date(segment.date_fin, lang))
            else:
                name = _(u"Le %s") % format_date(segment.date_deb, lang)
            if segment.motif:
                name += u" (%s)" % segment.motif
            segment.name = name

    # @api.onchange

    @api.onchange('modele_id')
    def _onchange_modele_id(self):
        if self.modele_id:
            self.creneau_ids = [(6, "ET OUIIIII", self.modele_id.creneau_ids.ids)]
            self.modele_id = False

    # Héritages

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get("restrict_date", False):
            order = 'date_deb DESC'
        # On détourne la fonction search pour peupler la liste de documents (onglet infos supplémentaires) à l'amorce de l'affichage de la vue
        res = super(OFHoraireSegment, self)._search(args, offset, limit, order, count, access_rights_uid)
        if self._context.get("restrict_date", False):
            today_str = fields.Date.today()
            records = self.browse(res)
            res = records.filtered(lambda s: s.date_fin >= today_str or not s.date_fin).ids
        return res

    # Autres méthodes

    @api.multi
    def format_str_list(self):
        """
        :return: Liste d'horaires à afficher
        :rtype: [ str, ...]
        """
        self.ensure_one()
        if not self.creneau_ids:
            return [u"Pas d'horaires définis"]
        # Regroupement des créneaux par jour (dictionnaire {jour: [heures]})
        horaires_dict = {}
        jour_prec = False
        jours = []  # Pour conserver les jours dans l'ordre croissant
        for creneau in self.creneau_ids:
            if creneau.jour_id != jour_prec:
                jour_prec = creneau.jour_id
                horaires_dict[jour_prec] = []
                jours.append(jour_prec)
            horaires_dict[jour_prec].append(hours_to_strs(creneau.heure_debut, creneau.heure_fin))

        # Regroupement des jours avec des créneaux identiques (liste [[jour1, jour2], [jour3]...])
        jour_groups = []
        for jour in jours:
            horaires = horaires_dict[jour]
            for jour_group in jour_groups:
                if horaires_dict[jour_group[0]] == horaires:
                    jour_group.append(jour)
                    break
            else:
                jour_groups.append([jour])

        # Passage en format texte
        result = []
        for jours in jour_groups:
            jours_str = ""
            while jours:
                if jours_str:
                    jours_str += ", "
                jour_deb = jours.pop(0)
                jour_fin = jour_deb
                while jours and jours[0].numero == jour_fin.numero + 1:
                    jour_fin = jours.pop(0)

                jours_str += jour_deb.abr
                if jour_fin != jour_deb:
                    jours_str += "-" + jour_fin.abr
            horaires_str = ", ".join(["%s-%s" % h
                                      for h in horaires_dict[jour_deb]])
            result.append(jours_str + " : " + horaires_str)
        return result

    @api.model
    def recompute_permanent_date_fin(self, employee_id, seg_type='regular'):
        """#TODO Cette fonction sera couteuse en temp de calcul au fil des ajout d'horaires permanents
        Une meilleure façon de faire serait de recalculer directement depuis le wizard d'horaires seulement les segments concernés
        mais on est dans l'hyper urgence alors on verra plus tard
        """
        seg_perm = self.search(
            [('employee_id', '=', employee_id), ('permanent', '=', True), ('type', '=', seg_type)], order="date_deb")
        un_jour = timedelta(days=1)
        if not seg_perm:
            return
        for i_seg in range(len(seg_perm) - 1):  # tous les segment sauf le dernier
            seg = seg_perm[i_seg]
            # le segment termine la veille du début du segment suivant
            fin_da = fields.Date.from_string(seg_perm[i_seg + 1].date_deb) - un_jour
            seg.date_fin = fields.Date.to_string(fin_da)
        seg_perm[-1].date_fin = False

    @api.multi
    def convert_segments_to_list(self):
        result = []
        for segment in self:
            creneaux_dict = {i+1: [] for i in xrange(7)}
            for creneau in segment.creneau_ids:
                creneaux_dict[creneau.jour_number].append([creneau.heure_debut, creneau.heure_fin])
            result.append([segment.date_deb, segment.date_fin, creneaux_dict])
        return result


class OFHorairesCreneau(models.Model):
    _name = "of.horaire.creneau"
    _order = "jour_number, heure_debut"

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u'Oups ! On dirait que ce créneau existe déjà.'),
        ('heure_debut_fin_constraint', 'CHECK ( heure_debut <= heure_fin )',
         _(u"L'heure de début doit être antérieure à l'heure de fin.")),
        ('heures_sont_des_heures_constraint',
         'CHECK ( heure_debut <= 24 AND heure_debut >= 0 AND heure_fin <= 24 AND heure_fin >= 0)',
         _(u"Les horaires doivent se trouver entre 0 et 24."))
    ]

    name = fields.Char(u"Créneau", compute="_compute_name", store=True)
    jour_id = fields.Many2one("of.jours", string="Jour", required=True)
    jour_number = fields.Integer(related="jour_id.numero", store=True)
    heure_debut = fields.Float(string=u"Heure de début", digits=(12, 5), required=True)
    heure_fin = fields.Float(string=u"Heure de fin", digits=(12, 5), required=True)

    @api.multi
    @api.depends("jour_id", "heure_debut", "heure_fin")
    def _compute_name(self):
        for creneau in self:
            creneau.name = (creneau.jour_id and creneau.jour_id.abr + ' ' or '') + \
                ' - '.join(hours_to_strs(creneau.heure_debut, creneau.heure_fin))

    @api.model
    def create_if_necessary(self, hor_md, hor_mf, hor_ad, hor_af, jour_ids):
        res = {
            'create_ids': [],
            'exist_ids': [],
        }
        for jour_id in jour_ids:
            for debut, fin in [(hor_md, hor_mf), (hor_ad, hor_af)]:
                if float_compare(debut, fin, 5) != 0:
                    creneau = self.search([
                        ('jour_id', '=', jour_id),
                        ('heure_debut', '<=', debut + 0.00005),  # éviter les erreurs d'arrondi
                        ('heure_debut', '>=', debut - 0.00005),
                        ('heure_fin', '<=', fin + 0.00005),
                        ('heure_fin', '>=', fin - 0.00005),
                    ], limit=1)
                    if not creneau:
                        vals = {
                            'jour_id': jour_id,
                            'heure_debut': debut,
                            'heure_fin': fin,
                        }
                        creneau = self.create(vals)
                        res['create_ids'].append(creneau.id)
                    else:
                        res['exist_ids'].append(creneau.id)
        return res

    @api.multi
    def format_str_list(self):
        """
        :return: Liste d'horaires à afficher
        :rtype: [ str, ...]
        """
        if not self:
            return [u"Aucun créneau horaire défini"]
        # Regroupement des créneaux par jour (dictionnaire {jour: [heures]})
        horaires_dict = {}
        jour_prec = False
        jours = []  # Pour conserver les jours dans l'ordre croissant
        for creneau in self:
            if creneau.jour_id != jour_prec:
                jour_prec = creneau.jour_id
                horaires_dict[jour_prec] = []
                jours.append(jour_prec)
            horaires_dict[jour_prec].append(hours_to_strs(creneau.heure_debut, creneau.heure_fin))

        # Regroupement des jours avec des créneaux identiques (liste [[jour1, jour2], [jour3]...])
        jour_groups = []
        for jour in jours:
            horaires = horaires_dict[jour]
            for jour_group in jour_groups:
                if horaires_dict[jour_group[0]] == horaires:
                    jour_group.append(jour)
                    break
            else:
                jour_groups.append([jour])

        # Passage en format texte
        result = []
        for jours in jour_groups:
            jours_str = ""
            while jours:
                if jours_str:
                    jours_str += ", "
                jour_deb = jours.pop(0)
                jour_fin = jour_deb
                while jours and jours[0].numero == jour_fin.numero + 1:
                    jour_fin = jours.pop(0)

                jours_str += jour_deb.abr
                if jour_fin != jour_deb:
                    jours_str += "-" + jour_fin.abr
            horaires_str = ", ".join(["%s-%s" % h
                                      for h in horaires_dict[jour_deb]])
            result.append(jours_str + " : " + horaires_str)
        return result


class OFHorairesModele(models.Model):
    _name = "of.horaire.modele"

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u"Le nom d'un modèle doit être unique."),
    ]

    name = fields.Char(u"Nom du modèle")
    creneau_ids = fields.Many2many(
        'of.horaire.creneau', 'modele_creneaux', 'modele_id', 'creneau_id', string=u"Créneaux"
    )
    active = fields.Boolean(string="Actif", default=True)


class Users(models.Model):
    _inherit = 'res.users'

    of_color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D",
                              oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0",
                              oldname="color_bg")

    @api.multi
    def write(self, vals):
        res = super(Users, self).write(vals)
        if not vals.get('no_rebounce') and (vals.get('of_color_ft') or vals.get('of_color_bg') or vals.get('tz')):
            emp_vals = {}
            if vals.get('of_color_ft'):
                emp_vals.update({'of_color_ft': vals['of_color_ft'], 'no_rebounce': True})
            if vals.get('of_color_bg'):
                emp_vals.update({'of_color_bg': vals['of_color_bg'], 'no_rebounce': True})
            if vals.get('tz'):
                emp_vals.update({'of_tz': vals['tz']})
            self.mapped('employee_ids').write(emp_vals)
        return res

    @api.model
    def create(self, vals):
        user = super(Users, self).create(vals)
        if user.employee_ids:
            if vals.get("of_color_ft", False) and not vals.get("no_rebounce", False):
                user.employee_ids.write({'of_color_ft': vals.get("of_color_ft", False), 'no_rebounce': True})
            if vals.get("of_color_bg", False) and not vals.get("no_rebounce", False):
                user.employee_ids.write({'of_color_bg': vals.get("of_color_bg", False), 'no_rebounce': True})
        # Création automatique employee sur création utilisateur? -> non: utilisateurs portail
        return user


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def get_jours_feries(self, date_debut, date_fin):
        u"""
            Renvois un dictionnaire de jours fériés avec pour clé la date et pour valeur le nom du jour férié.
            Contient tous les jours fériés compris entre date_debut et date_fin inclus.
            date_debut et date_fin peuvent être de type Datetime, Date ou basestring
            """
        if not len(self):
            company = self.env.user.company_id
        else:
            company = self[0]
        # Pour la prise de RDV en ligne, on s'affranchit des droits sur la société
        company = company.sudo()
        if isinstance(date_debut, basestring):
            date_debut_da = fields.Date.from_string(date_debut)
        elif isinstance(date_debut, (date, datetime)):
            date_debut_da = date_debut
        if isinstance(date_fin, basestring):
            date_fin_da = fields.Date.from_string(date_fin)
        elif isinstance(date_fin, (date, datetime)):
            date_fin_da = date_fin
        country = company.country_id
        holi_dict = holidays.CountryHoliday(country.code or 'FR', years=[date_debut_da.year, date_fin_da.year])
        res = {}
        for key, val in holi_dict.iteritems():
            if date_debut_da <= key <= date_fin_da:
                res[str(key)] = val
        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_colors", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_colors", oldname="color_bg")
    of_telephones = fields.Text(string=u"Téléphones", compute="_compute_of_telephones")

    @api.depends("user_ids")
    def _compute_colors(self):
        for partner in self:
            if partner.user_ids:
                partner.of_color_ft = partner.user_ids[0].of_color_ft
                partner.of_color_bg = partner.user_ids[0].of_color_bg
            else:
                partner.of_color_ft = "#0D0D0D"
                partner.of_color_bg = "#F0F0F0"

    @api.multi
    @api.depends('phone', 'mobile')
    def _compute_of_telephones(self):
        for partner in self:
            partner.of_telephones = '\n'.join([phone for phone in (partner.mobile, partner.phone) if phone])


class MeetingType(models.Model):
    _inherit = 'calendar.event.type'

    active = fields.Boolean("Actif", default=True)


class Meeting(models.Model):
    _inherit = "calendar.event"

    # Search

    def _search_lat(self, operator, operand):
        partners = self.env['res.partner']
        companies = self.env['res.company']
        for meeting in self:
            if meeting.of_lieu and meeting.of_lieu == "onsite":
                companies |= meeting.of_lieu_company_id  # of_lieu_company_id est res.company
            elif meeting.of_lieu and meeting.of_lieu == "offsite":
                partners |= meeting.of_lieu_rdv_id
            elif meeting.of_lieu and meeting.of_lieu == "phone":
                continue
            else:
                continue
        partners = partners.search([('id', 'in', partners._ids), ('geo_lat', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.geo_lat', operator, operand)])
        return [('id', 'in', self.env['calendar.event'].search(['|', '&', ('of_lieu_company_id', 'in', companies.ids),
                                                                ('of_lieu', '=', 'onsite'),
                                                                '&', ('of_lieu_rdv_id', 'in', partners.ids),
                                                                ('of_lieu', '=', 'offsite')]).ids)]

    def _search_lng(self, operator, operand):
        partners = self.env['res.partner']
        companies = self.env['res.company']
        for meeting in self:
            if meeting.of_lieu and meeting.of_lieu == "onsite":
                companies |= meeting.of_lieu_company_id  # of_lieu_company_id est res.company
            elif meeting.of_lieu and meeting.of_lieu == "offsite":
                partners |= meeting.of_lieu_rdv_id
            elif meeting.of_lieu and meeting.of_lieu == "phone":
                continue
            else:
                continue
        partners = partners.search([('id', 'in', partners._ids), ('geo_lng', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.geo_lng', operator, operand)])
        return [('id', 'in', self.env['calendar.event'].search(['|', '&', ('of_lieu_company_id', 'in', companies.ids),
                                                                ('of_lieu', '=', 'onsite'),
                                                                '&', ('of_lieu_rdv_id', 'in', partners.ids),
                                                                ('of_lieu', '=', 'offsite')]).ids)]

    def _search_precision(self, operator, operand):
        partners = self.env['res.partner']
        companies = self.env['res.company']
        for meeting in self:
            if meeting.of_lieu and meeting.of_lieu == "onsite":
                companies |= meeting.of_lieu_company_id  # of_lieu_company_id est res.company
            elif meeting.of_lieu and meeting.of_lieu == "offsite":
                partners |= meeting.of_lieu_rdv_id
            elif meeting.of_lieu and meeting.of_lieu == "phone":
                continue
            else:
                continue
        partners = partners.search([('id', 'in', partners._ids), ('precision', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.precision', operator, operand)])
        return [('id', 'in', self.env['calendar.event'].search(['|', '&', ('of_lieu_company_id', 'in', companies.ids),
                                                                ('of_lieu', '=', 'onsite'),
                                                                '&', ('of_lieu_rdv_id', 'in', partners.ids),
                                                                ('of_lieu', '=', 'offsite')]).ids)]

    # redefinition
    description = fields.Html('Description', states={'done': [('readonly', True)]})
    location = fields.Char('Location', compute="_compute_location", store=True, track_visibility='onchange',
                           help="Location of Event")

    of_lieu = fields.Selection([
        ("onsite", "Dans les locaux"),
        ("phone", u"Au téléphone"),
        ("offsite", u"À l'exterieur"),
        ("custom", "Adresse manuelle"),
    ], string="Lieu du RDV", required=True, default="onsite")
    of_lieu_company_id = fields.Many2one("res.company",
                                         string=u"(Précisez)")
    of_lieu_rdv_id = fields.Many2one("res.partner", string=u"(Précisez)")
    of_lieu_address_street = fields.Char(string="Rue")
    of_lieu_address_street2 = fields.Char(string="Rue (2)")
    of_lieu_address_city = fields.Char(string="Ville")
    of_lieu_address_state_id = fields.Many2one("res.country.state", string=u"Région")
    of_lieu_address_zip = fields.Char(string="Code postal")
    of_lieu_address_country_id = fields.Many2one("res.country", string="Pays")
    of_on_phone = fields.Boolean(u'Au téléphone', compute="_compute_on_phone")
    of_color_partner_id = fields.Many2one(
        "res.partner", "Partner whose color we will take", compute='_compute_color_partner', store=False)
    of_geo_lat = fields.Float(
        string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", compute="_compute_geo",
        store=False, search='_search_lat')
    of_geo_lng = fields.Float(
        string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", compute="_compute_geo",
        store=False, search='_search_lng')
    of_precision = fields.Selection(
        GEO_PRECISION, default='no_address', compute="_compute_geo", store=False, search='_search_precision',
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")

    """
    These fields would be necessary if use_contacts="0" in <calendar>. See event_data_transform function in .js file

    of_color_ft = fields.Char(string="Couleur de texte", help="Couleur de texte de l'utilisateur",
                              compute="_compute_of_color")
    of_color_bg = fields.Char(string="Couleur de fond", help="Couleur de fond de l'utilisateur",
                              compute="_compute_of_color")

    @api.multi
    @api.depends('of_color_partner_id')
    def _compute_of_color(self):
        for meeting in self:
            meeting.of_color_bg = meeting.of_color_partner_id.of_color_bg
            meeting.of_color_ft = meeting.of_color_partner_id.of_color_ft
    """

    # @api.depends

    @api.multi
    @api.depends("of_lieu", "of_lieu_company_id", "of_lieu_rdv_id", "of_precision", "of_lieu_address_street",
                 "of_lieu_address_street2", "of_lieu_address_city", "of_lieu_address_state_id", "of_lieu_address_zip",
                 "of_lieu_address_country_id")
    def _compute_location(self):
        for meeting in self:
            if meeting.of_precision != "no_address":
                le_tab = []
                le_texte = ""
                # On remplit le tableau puis on crée le texte
                if meeting.of_lieu_address_street:
                    le_tab.append(meeting.of_lieu_address_street)
                if meeting.of_lieu_address_street2:
                    le_tab.append(meeting.of_lieu_address_street2)
                if meeting.of_lieu_address_city and meeting.of_lieu_address_zip:
                    le_tab.append(meeting.of_lieu_address_zip + " " + meeting.of_lieu_address_city)
                elif meeting.of_lieu_address_city:
                    le_tab.append(meeting.of_lieu_address_city)
                elif meeting.of_lieu_address_zip:
                    le_tab.append(meeting.of_lieu_address_zip)
                if meeting.of_lieu_address_state_id:
                    le_tab.append(meeting.of_lieu_address_state_id.name)
                if meeting.of_lieu_address_country_id:
                    le_tab.append(meeting.of_lieu_address_country_id.name)
                if len(le_tab) > 0:
                    le_texte += le_tab[0]
                for i in range(1, len(le_tab)):
                    le_texte += ", " + le_tab[i]
                meeting.location = le_texte

    @api.multi
    @api.depends("of_lieu")
    def _compute_on_phone(self):
        for meeting in self:
            if meeting.of_lieu and meeting.of_lieu == "phone":
                meeting.of_on_phone = True

    @api.multi
    @api.depends('user_id')
    def _compute_color_partner(self):
        for meeting in self:
            if meeting.user_id.partner_id in meeting.partner_ids:
                meeting.color_partner_id = meeting.user_id.partner_id
            else:
                meeting.color_partner_id = (filter(lambda partner: partner.user_ids, meeting.partner_ids) or [False])[0]

    @api.multi
    @api.depends("of_lieu", "of_lieu_company_id", "of_lieu_rdv_id")
    def _compute_geo(self):
        for meeting in self:
            if meeting.of_lieu and meeting.of_lieu in ('onsite', 'offsite'):  # dans les locaux ou à l'extérieur
                if meeting.of_lieu == "onsite":
                    address = meeting.of_lieu_company_id
                else:
                    address = meeting.of_lieu_rdv_id
                vals = {
                    "of_lieu_address_street": address.street,
                    "of_lieu_address_street2": address.street2,
                    "of_lieu_address_city": address.city,
                    "of_lieu_address_state_id": address.state_id.id,
                    "of_lieu_address_zip": address.zip,
                    "of_lieu_address_country_id": address.country_id.id,
                    'of_geo_lat': address.geo_lat,
                    'of_geo_lng': address.geo_lng,
                    'of_precision': address.precision,
                }
            elif meeting.of_lieu and meeting.of_lieu == "phone":  # au téléphone
                vals = {
                    "of_lieu_address_street": False,
                    "of_lieu_address_street2": False,
                    "of_lieu_address_city": False,
                    "of_lieu_address_state_id": False,
                    "of_lieu_address_zip": False,
                    "of_lieu_address_country_id": False,
                    'of_geo_lat': 0,
                    'of_geo_lng': 0,
                    'of_precision': 'no_address',
                }
            else:  # custom
                vals = {
                    'of_geo_lat': 0,
                    'of_geo_lng': 0,
                    'of_precision': 'not_tried',
                }
            meeting.update(vals)

    # @api.onchange

    @api.onchange('of_lieu')
    def _onchange_lieu(self):
        self.ensure_one()
        if not self.of_lieu or self.of_lieu == "phone":  # réinitialise
            self.of_lieu_rdv_id = False
            self.of_lieu_company_id = False
        elif self.of_lieu == "onsite":  # on site
            self.of_lieu_company_id = self.user_id.company_id.id
            self.of_lieu_rdv_id = self.user_id.company_id.partner_id.id
        else:  # off site
            self.of_lieu_company_id = False

    @api.onchange('of_lieu_company_id')
    def _onchange_lieu_company_id(self):
        self.ensure_one()
        if not self.of_lieu or not self.of_lieu == "onsite":
            return
        if not self.of_lieu_company_id:
            return
        self.of_lieu_rdv_id = self.of_lieu_company_id.partner_id.id

    # Héritages

    @api.multi
    def write(self, vals):
        if vals.get('of_lieu_rdv_id', False) or vals.get('of_lieu_company_id', False):
            lieu = vals.get('of_lieu', False) or self.env["calendar.event"].browse(self._ids[0]).of_lieu
            if lieu in ('onsite', 'offsite'):
                if lieu == "onsite":
                    address = self.env["res.company"].browse(vals.get("of_lieu_company_id", False)).partner_id
                else:
                    address = self.env["res.partner"].browse(vals.get("of_lieu_rdv_id"))
                vals["of_lieu_address_street"] = address.street
                vals["of_lieu_address_street2"] = address.street2
                vals["of_lieu_address_city"] = address.city
                vals["of_lieu_address_state_id"] = address.state_id.id
                vals["of_lieu_address_zip"] = address.zip
                vals["of_lieu_address_country_id"] = address.country_id.id
            elif lieu == "phone":
                vals["of_lieu_address_street"] = False
                vals["of_lieu_address_street2"] = False
                vals["of_lieu_address_city"] = False
                vals["of_lieu_address_state_id"] = False
                vals["of_lieu_address_zip"] = False
                vals["of_lieu_address_country_id"] = False
                vals["of_geo_lat"] = False
                vals["of_geo_lng"] = False
                vals["of_precision"] = "no_address"
        return super(Meeting, self).write(vals)

    @api.model
    def create(self, vals):
        """
        En cas de création par google agenda, le champs "location" peut etre renseigné,
        or dans ce module on transforme ce champ en champ calculé
        """
        lieu = vals.get('of_lieu', False)
        if not lieu:
            vals["of_lieu"] = "custom"
        else:
            if lieu in ('onsite', 'offsite'):
                if lieu == "onsite":
                    address = self.env["res.company"].browse(vals.get("of_lieu_company_id")).partner_id
                else:
                    address = self.env["res.partner"].browse(vals.get("of_lieu_rdv_id"))
                vals["of_lieu_address_street"] = address.street
                vals["of_lieu_address_street2"] = address.street2
                vals["of_lieu_address_city"] = address.city
                vals["of_lieu_address_state_id"] = address.state_id.id
                vals["of_lieu_address_zip"] = address.zip
                vals["of_lieu_address_country_id"] = address.country_id.id
            elif lieu == "phone":
                vals["of_lieu_address_street"] = False
                vals["of_lieu_address_street2"] = False
                vals["of_lieu_address_city"] = False
                vals["of_lieu_address_state_id"] = False
                vals["of_lieu_address_zip"] = False
                vals["of_lieu_address_country_id"] = False
        loc = vals.get("location", False)
        if loc:  # created from google agenda most likely
            vals["of_lieu_address_street"] = loc
            vals["of_lieu"] = "custom"
        return super(Meeting, self).create(vals)


class CalendarMixin(models.AbstractModel):
    _name = "of.calendar.mixin"

    state_int = fields.Integer(string=u"Valeur d'état", compute="_compute_state_int", help=u"valeur allant de 0 à 3 inclus")

    def _compute_state_int(self):
        """
        Function to give an integer value (0,1,2 or 3) depending on the state. ONLY 4 values are implemented.
        A CSS class 'of_calendar_state_#{self.state_int} will be given in CalendarView.event_data_transform.
        See .less and .js files for further information
        """
        raise NotImplementedError("A class inheriting from this one must implement a '_compute_state_int' function")

    @api.model
    def get_state_int_map(self):
        """
        Returns a tuple of dictionaries. Each one contains 'value' and 'label' attributes.
        'value' ranges from 0 to 3 included.
        'label' is a string that will be displayed in the caption.
        See template 'CalendarView.sidebar.captions'
        """
        raise NotImplementedError("A class inheriting from this one must implement a 'get_state_int_map' function")
