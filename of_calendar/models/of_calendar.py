# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import json
import pytz
from copy import deepcopy

def hours_to_strs(*hours):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return tuple("%dh%02d" % (hour, round((hour % 1) * 60)) if hour % 1 else "%dh" % (hour) for hour in hours)
    #return tuple("%dh" % (hour) + (hour % 1 and "%02d" % (round((hour % 1) * 60)) or "") for hour in hours)

def se_chevauchent(debut_1, fin_1, debut_2, fin_2, strict=True):
    """renvoi True si les horaires se chevauchent, False sinon."""
    if strict:
        return debut_1 < fin_2 and debut_2 < fin_1
    return debut_1 <= fin_2 and debut_2 <= fin_1

@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

def jour_abr_2_nb(str):
    return str.replace(u'"lun."', u'"1"')\
              .replace(u'"mar."', u'"2"')\
              .replace(u'"mer."', u'"3"')\
              .replace(u'"jeu."', u'"4"')\
              .replace(u'"ven."', u'"5"')\
              .replace(u'"sam."', u'"6"')\
              .replace(u'"dim."', u'"7"')

# @TODO: revoir les nom des fonctions pour qu'ils soient plus explicites


class HREmployee(models.Model):
    _inherit = "hr.employee"

    def _default_of_tz(self):
        return self.env.user.tz or 'Europe/Paris'

    @api.depends('of_tz')
    def _compute_of_tz_offset(self):
        for employee in self:
            employee.of_tz_offset = datetime.now(pytz.timezone(employee.of_tz or 'GMT')).strftime('%z')

    @api.multi
    def check_no_overlapping(self):
        for employee in self:
            for i in range(1, 8):
                creneaux_du_jour = employee.of_creneau_ids.filtered(lambda x: x.jour_number == i)
                la_len = len(creneaux_du_jour)
                for j in range(la_len):
                    for k in range(j+1, la_len):
                        d1 = creneaux_du_jour[j].heure_debut
                        f1 = creneaux_du_jour[j].heure_fin
                        d2 = creneaux_du_jour[k].heure_debut
                        f2 = creneaux_du_jour[k].heure_fin
                        if se_chevauchent(d1, f1, d2, f2):
                            # raise UserError(u"Oups! Des créneaux se chevauchent")
                            return False
                creneaux_temp_du_jour = employee.of_creneau_temp_ids.filtered(lambda jour: jour.jour_number == i)
                la_len = len(creneaux_temp_du_jour)
                for j in range(la_len):
                    for k in range(j+1, la_len):
                        d1 = creneaux_temp_du_jour[j].heure_debut
                        f1 = creneaux_temp_du_jour[j].heure_fin
                        d2 = creneaux_temp_du_jour[k].heure_debut
                        f2 = creneaux_temp_du_jour[k].heure_fin
                        if se_chevauchent(d1, f1, d2, f2):
                            # raise UserError(u"Oups! Des créneaux se chevauchent")
                            return False
        return True

    of_tz = fields.Selection(
        _tz_get, string='Fuseau horaire', required=True, default=lambda self: self._default_of_tz(),
        help=u"Le fuseau horaire de l'employé")
    of_tz_offset = fields.Char(compute='_compute_of_tz_offset', string='Timezone offset', invisible=True)
    u"""Création horaires avancés"""
    of_mode_horaires = fields.Selection([
        ("easy", "Facile"),
        ("advanced", u"Avancé")], string="Mode de Sélection des horaires", required=True, default="easy")
    of_profil_id = fields.Many2one("of.horaires.profil", "Profil")
    of_creneau_ids = fields.Many2many("of.horaires.creneau", "employee_creneaux", "employee_id", "creneau_id", string=u"Créneaux", order="jour_number, heure_debut")
    of_creneau_temp_ids = fields.Many2many("of.horaires.creneau", "employee_creneaux_temp", "employee_id", "creneau_id", string=u"Créneaux", order="jour_number, heure_debut")
    of_creneau_temp_start = fields.Date(string=u"Début des horaires temporaires")
    of_creneau_temp_stop = fields.Date(string="Fin des horaires temporaires")
    of_archive_horaires = fields.Text(string="Archive des horaires")
    of_archive_horaires_temp = fields.Text(string="Archive des horaires temporaires")
    of_horaires_du_jour = fields.Text(string=u"Horaires d'aujourd'hui", compute="_compute_horaires_du_jour")

    of_hor_md = fields.Float(string=u'Matin début', digits=(12, 1), default=9)
    of_hor_mf = fields.Float(string='Matin fin', digits=(12, 1), default=12)
    of_hor_ad = fields.Float(string=u'Après-midi début', digits=(12, 1), default=14)
    of_hor_af = fields.Float(string=u'Après-midi fin', digits=(12, 1), default=18)
    of_jour_ids = fields.Many2many('of.jours', 'employee_jours_rel', 'employee_id', 'jour_id', string='Jours travaillés', default=lambda self: self._get_default_jours())

    of_address_depart_id = fields.Many2one('res.partner', string=u'Adresse de départ')
    of_address_retour_id = fields.Many2one('res.partner', string='Adresse de retour')

    of_color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0", oldname="color_bg")

    _sql_constraints = [
        ('hor_md_mf_constraint', 'CHECK ( of_hor_md <= of_hor_mf )', _(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")),
        ('hor_mf_ad_constraint', 'CHECK ( of_hor_mf <= of_hor_ad )', _(u"L'Heure de fin de matinée doit être antérieure à l'heure de début d'après-midi")),
        ('hor_ad_af_constraint', 'CHECK ( of_hor_ad <= of_hor_af )', _(u"L'Heure de début d'après-midi doit être antérieure à l'heure de fin d'après-midi")),
        ('of_creneau_temp_start_stop_constraint', 'CHECK ( of_creneau_temp_start <= of_creneau_temp_stop )', _(u"La date de début de validité doit être antérieure ou égale à celle de fin")),
    ]

    _constraints = [
        (check_no_overlapping, u'Vous ne pourrez pas sauvegarder tant que des créneaux se chevauchent!', []),
    ]

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    @api.multi
    @api.depends('of_archive_horaires', 'of_archive_horaires_temp')
    def _compute_horaires_du_jour(self):
        horaires_today = self.get_horaires_date(fields.Date.today())
        for employee in self:
            employee.of_horaires_du_jour = "\n".join(hours_to_strs(horaires_today[employee.id]))

    @api.onchange('of_address_depart_id')
    def _onchange_address_depart_id(self):
        self.ensure_one()
        if self.of_address_depart_id:
            self.of_address_retour_id = self.of_address_depart_id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        self.ensure_one()
        if self.user_id:
            self.of_tz = self.user_id.tz
            self.of_color_ft = self.user_id.of_color_ft
            self.of_color_bg = self.user_id.of_color_bg

    @api.onchange('of_hor_md')
    def _onchange_hor_md(self):
        self.ensure_one()
        if self.of_hor_md and self.of_hor_mf and self.of_hor_md > self.of_hor_mf:
            raise UserError(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")

    @api.onchange('of_hor_mf')
    def _onchange_hor_mf(self):
        self.ensure_one()
        if self.of_hor_md and self.of_hor_mf and self.of_hor_md > self.of_hor_mf:
            raise UserError(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")
        elif self.of_hor_mf and self.of_hor_ad and self.of_hor_mf > self.of_hor_ad:
            raise UserError(u"L'Heure de fin de matinée doit être antérieure à l'heure de début d'après-midi")

    @api.onchange('of_hor_ad')
    def _onchange_hor_ad(self):
        self.ensure_one()
        if self.of_hor_ad and self.of_hor_af and self.of_hor_ad > self.of_hor_af:
            raise UserError(u"L'Heure de début d'après-midi doit être antérieure à l'heure de fin d'après-midi")
        elif self.of_hor_mf and self.of_hor_ad and self.of_hor_mf > self.of_hor_ad:
            raise UserError(u"L'Heure de fin de matinée doit être antérieure à l'heure de début d'après-midi")

    @api.onchange('of_hor_af')
    def _onchange_hor_af(self):
        self.ensure_one()
        if self.of_hor_ad and self.of_hor_af and self.of_hor_ad > self.of_hor_af:
            raise UserError(u"L'Heure de début d'après-midi doit être antérieure à l'heure de fin d'après-midi")

    @api.model
    def get_working_hours_fields(self):
        return {
            "morning_start_field": "of_hor_md",
            "morning_end_field": "of_hor_mf",
            "afternoon_start_field": "of_hor_ad",
            "afternoon_end_field": "of_hor_af"
        }

    @api.onchange("of_creneau_ids", "of_creneau_temp_ids")
    def _onchange_creneaux(self):
        if not self.check_no_overlapping():
            raise UserError(u"Oups! Des créneaux se chevauchent. Veuillez vous assurer que ce ne soit plus le cas avant de sauvegarder.")

    @api.onchange("of_creneau_temp_start")
    def _onchange_of_creneau_temp_start(self):
        self.ensure_one()
        if self.of_creneau_temp_start:
            date_deb = fields.Date.from_string(self.of_creneau_temp_start)
            date_fin = date_deb + timedelta(days=6)
            self.of_creneau_temp_stop = fields.Date.to_string(date_fin)

    @api.multi
    def possede_creneau(self, creneau_id):
        u"""vérifie que tous les employés présents dans self possèdent tel ou tel créneau.
            Ne prend pas en compte les créneaux temporaires."""
        if len(self._ids) == 0:
            return None
        for employee in self:
            if len(employee.of_creneau_ids.filtered(lambda x: x.id == creneau_id)) > 0:
                continue
            else:
                return False
        return True

    @api.multi
    def archiver_horaires(self):
        date_today_str = fields.Date.today()
        date_today_da = fields.Date.from_string(date_today_str)
        un_jour = timedelta(days=1)
        for employee in self:
            """Récupérer l'archive actuelle, si la date d'aujourd'hui existe déjà dans l'archive, on la remplace"""
            archive = employee.of_archive_horaires
            if archive:
                morceaux_list = archive.split(u"\n")
                for morceau in morceaux_list:
                    la_date_str = morceau[2:12]  # la date commence au 3eme caractère du morceau
                    if date_today_str == la_date_str:
                        morceaux_list.remove(morceau)
                        break
            else:
                morceaux_list = []
            """Ajout date d'hier si besoin"""
            if len(morceaux_list) > 0:
                morceau = morceaux_list[-1]
                if morceau[15] == u'f':  # le dernier morceau de la liste n'a pas de date de fin.
                    date_hier_da = date_today_da - un_jour
                    date_hier_str = fields.Date.to_string(date_hier_da)
                    morceaux_list[-1] = morceau[:15] + u'"' + date_hier_str + u'"' + morceau[20:]
            """création de l'archive"""
            nouveau_morceau_dict = {}  # dict contenant les horaires de travail
            if employee.of_mode_horaires == u"advanced":  # mode avancé
                for creneau in employee.of_creneau_ids:
                    if creneau.jour_id.abr not in nouveau_morceau_dict:
                        nouveau_morceau_dict[creneau.jour_id.abr] = []
                    nouveau_morceau_dict[creneau.jour_id.abr].append((creneau.heure_debut, creneau.heure_fin))
            else:  # mode facile
                for jour in employee.of_jour_ids:
                    nouveau_morceau_dict[jour.abr] = [(employee.of_hor_md, employee.of_hor_mf), (employee.of_hor_ad, employee.of_hor_af)]
            if archive:
                nouveau_morceau_str = u'["%s", false, %s]' % (date_today_str, json.dumps(nouveau_morceau_dict))
            else:  # lors de la permière création d'horaires, on considère que l'employé avait ces horaires depuis sa création
                nouveau_morceau_str = u'["%s", false, %s]' % (employee.create_date[:10], json.dumps(nouveau_morceau_dict))
            morceaux_list.append(nouveau_morceau_str)
            nouvelle_archive = u"\n".join(morceaux_list)
            employee.of_archive_horaires = nouvelle_archive

    @api.multi
    def archiver_horaires_temp(self):
        for employee in self:
            archive = employee.of_archive_horaires_temp
            if archive:
                morceaux_list = archive.split("\n")
                """Vérification qu'il n'y a pas de chevauchement avec des dates d'horaires temporaires existants"""
                for morceau in morceaux_list:
                    la_liste = json.loads(morceau)
                    if se_chevauchent(la_liste[0], la_liste[1], employee.of_creneau_temp_start, employee.of_creneau_temp_stop, False):
                        raise UserError(u"OH oh! le système nous dit qu'il y a du chevauchement au niveau de l'archive des horaires temporaires.\n"
                                        u"Pour que tout se passe bien, veuillez sélectionner des dates de début et de fin qui ne chevauchent pas des dates de début et de fin existantes dans l'archive.\n"
                                        u"dates source du conflit: entre le %s et le %s" % (la_liste[0], la_liste[1]))
            else:
                morceaux_list = []
            """Création du nouveau morceau et de l'archive"""
            nouveau_morceau_dict = {}  # dict contenant les horaires de travail temporaire
            for creneau in employee.of_creneau_temp_ids:
                if creneau.jour_id.abr not in nouveau_morceau_dict:
                    nouveau_morceau_dict[creneau.jour_id.abr] = []
                nouveau_morceau_dict[creneau.jour_id.abr].append((creneau.heure_debut, creneau.heure_fin))
            nouveau_morceau_str = u'["%s", "%s", %s]' % (employee.of_creneau_temp_start, employee.of_creneau_temp_stop, json.dumps(nouveau_morceau_dict))
            morceaux_list.append(nouveau_morceau_str)
            morceaux_list.sort(key=lambda x: x[2:12])  # si quelqu'un ajoute des horaires temporaires antérieurs à ceux déjà ajouté, BIM FOOLPROOF
            nouvelle_archive = u"\n".join(morceaux_list)
            employee.of_archive_horaires_temp = nouvelle_archive

    @api.multi
    def get_archive_list_segments(self, jour_keys="number"):
        """Renvois l'archive des horaires des employés présents dans self sous forme de liste
        résultat sous forme {  employee_id :  [ [date_debut, date_fin, horaires_dict], ...],  ...  }"""
        res = {}
        for employee in self:
            res[employee.id] = {}
            if not employee.of_archive_horaires:
                continue
            archive_str = u'[%s]' % employee.of_archive_horaires.replace(u"\n", u",")
            if jour_keys == "number":
                archive_str = jour_abr_2_nb(archive_str)
            list_archive = json.loads(archive_str)
            if jour_keys == "number":
                for segment in list_archive:
                    horaires_dict = segment[2]
                    for k in horaires_dict:
                        horaires_dict[int(k)] = horaires_dict.pop(k)
            res[employee.id] = list_archive
        return res

    @api.multi
    def get_archive_list_segments_temp(self, jour_keys="number"):
        """Renvois l'archive des horaires temporaires des employés présents dans self sous forme de liste
        résultat sous forme {  employee_id :  [ [date_debut, date_fin, horaires_dict], ...],  ...  }"""
        res = {}
        for employee in self:
            res[employee.id] = {}
            if not employee.of_archive_horaires_temp:
                continue
            archive_str = u'[%s]' % employee.of_archive_horaires_temp.replace(u"\n", u",")
            if jour_keys == "number":
                archive_str = jour_abr_2_nb(archive_str)
            list_archive = json.loads(archive_str)  # json.loads nécessite des noms de propriétés entre double quotes
            if jour_keys == "number":
                for segment in list_archive:
                    horaires_dict = segment[2]
                    for k in horaires_dict:
                        horaires_dict[int(k)] = horaires_dict.pop(k)
            res[employee.id] = list_archive
        return res

    @api.multi
    def get_horaires_date(self, date_str):
        """renvois les horaires des employés présent dans self à la date donnée en paramètre.
        résultat sous forme { employee_id :  [(h_deb, h_fin), (h_deb, h_fin), ..] ,  .. }"""
        archive_horaires = self.get_archive_list_segments()
        archive_horaires_temp = self.get_archive_list_segments_temp()
        date_da = fields.Date.from_string(date_str)
        num_jour = date_da.isoweekday()  # entre 1 et 7
        res = {}
        for employee in self:
            res[employee.id] = []
            horaires_temp = archive_horaires_temp[employee.id]
            for segment in horaires_temp:  # la date demandée correspond-elle à des horaires temporaires pour cet employé?
                if se_chevauchent(date_str, date_str, segment[0], segment[1], False):  # la date demandée est sur un segment d'horaires temporaires
                    res[employee.id] = segment[2][num_jour]
                    break
            horaires = archive_horaires[employee.id]
            if not res[employee.id]:  # la date demandée n'est pas sur un segment d'horaires temporaires
                for segment in horaires:
                    if not segment[1]:  # le dernier segment horaires n'a pas de date de fin
                        res[employee.id] = num_jour in segment[2] and segment[2][num_jour] or []
                        break
                    if se_chevauchent(date_str, date_str, segment[0], segment[1], False):  # trouvé!
                        res[employee.id] = segment[2][num_jour]
                        break
        return res

    @api.model
    def get_horaires_date_model(self, date_str, archive_list_horaires, archive_list_horaires_temp):
        """renvois les horaires de l'employés dont les archives horaires sont données en paramètres à la date donnée.
        fonction pour éviter de faire des appels à get_archive_list_segments non nécessaires
        résultat sous forme [(h_deb, h_fin), (h_deb, h_fin), ..]"""
        date_da = fields.Date.from_string(date_str)
        num_jour = date_da.isoweekday()  # entre 1 et 7
        res = []
        for segment in archive_list_horaires_temp:  # la date demandée correspond-elle à des horaires temporaires pour cet employé?
            if se_chevauchent(date_str, date_str, segment[0], segment[1], False):  # la date demandée est sur un segment d'horaires temporaires
                res = segment[2][num_jour]
                break
        if not res:  # la date demandée n'est pas sur un segment d'horaires temporaires
            for segment in archive_list_horaires:
                if se_chevauchent(date_str, date_str, segment[0], segment[1], False):  # trouvé!
                    res = segment[2][num_jour]
                    break
        return res

    @api.model
    def get_horaires_list_dict(self, employee_ids, date_start, date_stop):
        """ renvois le résultat de la fusion des archives horaires et archives horaires temporaires des employés
        résultat sous forme { employee_id :  [(date_debut_da, date_fin_da, horaires_dict), (date_debut_da, date_fin_da, horaires_dict), ..] ,  .. }"""
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
        archive_list_horaires = self.browse(employee_ids).get_archive_list_segments()
        archive_list_horaires_temp = self.browse(employee_ids).get_archive_list_segments_temp()
        for employee in self.browse(employee_ids):
            res[employee.id] = []
            # en cas d'employés sur différentes timezones
            tz = pytz.timezone(employee.of_tz or "Europe/Paris")
            if mode_params == "datetime":
                date_start_local_dt = date_start_utc_dt.astimezone(tz)  # datetime local
                date_stop_local_dt = date_stop_utc_dt.astimezone(tz)  # datetime local
                date_start_str = fields.Date.to_string(date_start_local_dt).decode('utf-8')
                date_stop_str = fields.Date.to_string(date_stop_local_dt).decode('utf-8')
            else:
                date_start_str = date_start
                date_stop_str = date_stop

            # on récupère les horaires standards
            horaires_employee = archive_list_horaires[employee.id]
            horaires_utiles = []
            if len(horaires_employee) == 1:  # les seuls horaires standard connu, on considère qu'ils sont valable sur la periode demandée
                horaires_utiles.append([date_start_str, date_stop_str, horaires_employee[0][2]])
            elif len(horaires_employee) > 1:
                # on cherche les index de début et de fin
                index_start = -1
                index_stop = -1
                for i in range(len(horaires_employee)):

                    if index_start == -1:  # n'a pas été affecté
                        if not horaires_employee[i][1]:
                            index_start = index_stop = i
                        elif se_chevauchent(date_start_str, date_start_str, horaires_employee[i][0], horaires_employee[i][1], False):
                            index_start = i
                    if index_stop == -1:  # n'a pas été affecté
                        if not horaires_employee[i][1]:
                            index_stop = i
                        elif se_chevauchent(date_stop_str, date_stop_str, horaires_employee[i][0], horaires_employee[i][1], False):
                            index_stop = i
                    if index_start != -1 and index_stop != -1:  # on a trouvé les 2 indexes
                        break

                if index_start == index_stop:  # on a de la chance! l'employé n'a pas changé d'horaires entre les 2 dates demandées
                    horaires_utiles.append([date_start_str, date_stop_str, horaires_employee[index_start][2]])
                else:  # mince alors! l'employé a changé d'horaires entre les 2 dates demandées
                    horaires_utiles.append([date_start_str, horaires_employee[index_start][1], horaires_employee[index_start][2]])
                    for i in range(index_start + 1, index_stop):
                        horaires_utiles.append([horaires_employee[i][0], horaires_employee[i][1], horaires_employee[i][2]])
                    horaires_utiles.append([horaires_employee[index_stop][0], date_stop_str, horaires_employee[index_stop][2]])
            # On a la liste des horaires standards! \o/ maintenant on récupère si besoin la liste des horaires temporaires
            horaires_employee_temp = archive_list_horaires_temp[employee.id]
            horaires_temp_utiles = []
            if len(horaires_employee_temp) == 0:  # oups! pas d'horaires temporaires
                for j in range( len(horaires_utiles) ):
                    res[employee.id].append(horaires_utiles[j])
                continue
            # Sélection des horaires temporaires concernés
            for i in range(len(horaires_employee_temp)):
                if se_chevauchent(date_start_str, date_stop_str, horaires_employee_temp[i][0], horaires_employee_temp[i][1], False):
                    # chevauchement! ce créneau est à prendre en compte
                    if horaires_employee_temp[i][0] < date_start_str:  # on coupe ce qui dépasse
                        horaires_employee_temp[i][0] = date_start_str
                    if horaires_employee_temp[i][1] > date_stop_str:  # à gauche et à droite
                        horaires_employee_temp[i][1] = date_stop_str
                    horaires_temp_utiles.append(horaires_employee_temp[i])
            # OK! on a 2 listes de segments d'horaires sur un même intervalle, fiou!
            # FUUUUUUU-ZION!
            index_courant = 0
            while len(horaires_temp_utiles) > 0:
                segment_std = horaires_utiles[index_courant]
                segment_temp = horaires_temp_utiles.pop(0)
                while not se_chevauchent(segment_temp[0], segment_temp[1], segment_std[0], segment_std[1], False):
                    res[employee.id].append(horaires_utiles[index_courant])
                    index_courant += 1
                    segment_std = horaires_utiles[index_courant]

                date_debut_temp_da = fields.Date.from_string(segment_temp[0])
                date_debut_temp_da -= un_jour
                debut_temp_str = fields.Date.to_string(date_debut_temp_da).decode('utf-8')
                date_fin_temp_da = fields.Date.from_string(segment_temp[1])
                date_fin_temp_da += un_jour
                fin_temp_str = fields.Date.to_string(date_fin_temp_da).decode('utf-8')
                sous_seg_1 = deepcopy(segment_std)
                sous_seg_1[1] = debut_temp_str
                if segment_temp[1] <= segment_std[1]:
                    # le segment d'horaires temporaires est inclus dans le segment d'horaires standards
                    # un sous-segment a été créé, on modifie le segment courant
                    horaires_utiles[index_courant][0] = fin_temp_str
                    if horaires_utiles[index_courant][0] > horaires_utiles[index_courant][1]:
                        index_courant += 1
                else:  # le segment d'horaires temporaires chevauche 2 segments d'horaires standards
                    # on met à jour le prochain segment d'horaires standards
                    index_courant += 1
                    horaires_utiles[index_courant][0] = fin_temp_str

                if sous_seg_1[0] <= sous_seg_1[1]:  # est un vrai segment, on l'ajoute!
                    res[employee.id].append(sous_seg_1)
                res[employee.id].append(segment_temp)
            if index_courant < index_stop:
                for j in range(index_courant, index_stop + 1):
                    segment_std = horaires_employee[j]
                    res[employee.id].append(segment_std)

        # WHOO HOO on y est! \o/
        # le résultat est un dictionnaire avec les identifiants des employés en clés
        # les valeurs sont de la forme [ [debut, fin, horaires] ,  [debut, fin, horaires] ,  ... ]
        # avec un seul choix d'horaires possibles pour une date donnée
        return res

    @api.model
    def get_list_horaires_intersection(self, employee_ids=[], date_start=False, date_stop=False, horaires_list_dict=False):
        """renvois l'intersection des horaires des employés donnés en paramètre
        avec soit les dates connues, soit le horaires_list_dict
        résultat sous la forme [ (date_debut_da, date_fin_da, horaires_dict) ,  (date_debut_da, date_fin_da, horaires_dict) ,  ..]"""
        res = []
        if len(employee_ids) == 0:
            return res
        if not horaires_list_dict:
            horaires_list_dict = self.get_horaires_list_dict(employee_ids, date_start, date_stop)
        if len(employee_ids) == 1:
            res = horaires_list_dict[employee_ids[0]]
            return res
        emp_ids = list(employee_ids)
        while len(emp_ids) > 1:
            emp_1 = emp_ids.pop(0)
            emp_2 = emp_ids.pop(0)
            # on utilise -1 comme fake id pour la fusion des segments de 2 employés
            horaires_list_dict[-1] = self.get_intersection_horaires_segment(emp_1, emp_2, horaires_list_dict)
            emp_ids.insert(0, -1)  # rajout du fake id dans la liste d'ids
        res = horaires_list_dict[-1]
        return res

    @api.model
    def get_intersection_horaires_segment(self, employee1_id, employee2_id, segments_list_dict):
        """renvois l'intersection des horaires des employés donnés en paramètre
        résultat sous la forme [ (date_debut_da, date_fin_da, horaires_dict) ,  (date_debut_da, date_fin_da, horaires_dict) ,  ..]"""
        res = []
        if len(segments_list_dict[employee1_id]) == 0 or len(segments_list_dict[employee2_id]) == 0:
            return res
        un_jour = timedelta(days=1)
        segments_emp_1 = deepcopy(segments_list_dict[employee1_id])  # [(date_debut_da, date_fin_da, horaires_dict), (date_debut_da, date_fin_da, horaires_dict), ..]
        segments_emp_2 = deepcopy(segments_list_dict[employee2_id])
        pre_res = []
        """fusionner les listes de segments pour que les dates correspondent, en conservant les 2 horaires_dict à chaque fois"""
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
        # OK! on a une liste de segments avec 2 horaires_dict dans chaque. maintenant on fusionne les horaires_dict pour garder leur intersection
        for segment in pre_res:
            segment_fuz = (segment[0], segment[1], self.get_intersection_heures_dict(segment[2], segment[3]))
            res.append(segment_fuz)
        # YOUPI!
        return res

    @api.model
    def get_intersection_heures_dict(self, dict1, dict2):
        """fusionne 2 horaires_dict et renvois leur intersection
        résultat sous la forme { 1..7 :  [(h_debut, h_fin), (h_debut, h_fin)] }
        exemple: dict1[1] = [(9, 12)], dict2 = [(11, 14)]; res[1] = [(11, 12)]"""
        res = {}
        for i in range(1, 8):  # parcourir les jours de la semaine
            res[i] = []
            if i not in dict1 or i not in dict2:  # l'une des 2 listes est vide: pas d'intersection
                continue
            list1 = deepcopy(dict1[i])  # liste des créneaux travaillés pour le jour i
            list2 = deepcopy(dict2[i])  # liste des créneaux travaillés pour le jour i

            while len(list1) > 0 and len(list2) > 0:
                if se_chevauchent(list1[0][0], list1[0][1], list2[0][0], list2[0][1]):  # les 2 créneaux se chevauchent!
                    res[i].append( (max(list1[0][0], list2[0][0]) ,  min(list1[0][1], list2[0][1])) )  # intersection des 2 créneaux
                    # la nouvelle heure de début est l'heure de fin du créneau qui termine en premier
                    if list1[0][1] < list2[0][1]:  # le 1er créneau de list1 termine avant le premier créneau de list2
                        list1.pop(0)
                        list2[0][0] = len(list1) > 0 and list1[0][1] or list2[0][1]
                    elif list1[0][1] > list2[0][1]:  # le 1er créneau de list2 termine avant le premier créneau de list1
                        list2.pop(0)
                        list1[0][0] = len(list2) > 0 and list2[0][1] or list1[0][1]
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
    def get_horaires_effectif_date(self, date_str, horaires_list_dict):
        """fonction qui utilise le résultat de get_horaires_list_dict pour trouver les horaires à une date donnée
        résultat équivalent à celui de get_horaires_date
        résultat sous forme { employee_id :  [(h_deb, h_fin), (h_deb, h_fin), ..] ,  .. }"""
        res = {}
        date_da = fields.Date.from_string(date_str)
        num_jour = date_da.isoweekday()
        for employee_id in horaires_list_dict:
            segments = horaires_list_dict[employee_id]
            for segment in segments:
                if not segment[1]:  # segment sans date de fin
                    res[employee_id] = num_jour in segment[2] and segment[2][num_jour] or []
                    break
                if se_chevauchent(date_str, date_str, segment[0], segment[1], False):  # la date demandée est sur ce segment d'horaires
                    res[employee_id] = num_jour in segment[2] and segment[2][num_jour] or []
                    break
        return res

    @api.model
    def debut_sur_creneau(self, date_str, h_debut, list_segments):
        """renvois l'indexe du créneau de début si l'heure et la date sont dans les horaires, -1 sinon"""
        for segment in list_segments:
            if segment[0] <= date_str <= segment[1]:  # la date est sur ce segment
                date_da = fields.Date.from_string(date_str)
                num_jour = date_da.isoweekday()
                creneaux = num_jour in segment[2] and segment[2][num_jour]
                for i in range(len(creneaux)):  # creneau sous form (h_debut, h_fin)
                    creneau = creneaux[i]
                    if creneau[0] <= h_debut < creneau[1]:
                        return i
                else:
                    return -1
        return -1

    @api.model
    def get_min_max_time(self):
        """
        parcours toutes équipes pour trouver les heures minimales et maximales de travail.
        Appelée depuis la CalendarView si l'attribut 'working_hours' est à "1". Sert à restreindre la vue Calendar pour ne pas voir les heures entre 0 et min, ni celles entre max et 24
        renvois les valeurs en UTC
        /!| Cette fonction est appelée avant de savoir les dates de début et de fin. on prend donc tous les horaires possibles
        """
        min_time = self.env['ir.values'].get_default('res.config.settings', 'calendar_min_time')
        max_time = self.env['ir.values'].get_default('res.config.settings', 'calendar_max_time')

        """employees = self.env['hr.employee'].search([])
        min_time = False
        max_time = False
        min_equipe = False
        max_equipe = False
        today_da = fields.Date.from_string(fields.Date.today())

        list_horaires = employees.get_archive_list_segments()
        list_horaires_temp = employees.get_archive_list_segments_temp()

        for equipe in equipes:
            equipe_id = equipe.id
            tz = pytz.timezone(equipe.of_tz or "Europe/Paris")
            if equipe.mode_horaires == "easy":
                # On utilise le mode facile pour les horaires de cette équipe
                min_equipe = equipe.hor_md
                max_equipe = equipe.hor_af
            else: # On utilise le mode avancé pour les horaires de cette équipe
                # l'équipe a-t-elle des horaires temporaires sur cette recherche??
                if equipe.of_creneau_temp_stop:
                    creneaux_temp_travailles = equipe.of_creneau_temp_ids
                    for i in range(1,8):
                        creneaux_temp_du_jour = creneaux_temp_travailles.filtered(lambda x: x.jour_number == i)
                        if len(creneaux_temp_du_jour) == 0:
                            continue
                        if min_equipe == False:  # ==False pour éviter un éventuel 0.0 oublié
                            min_equipe = creneaux_temp_du_jour[0].heure_debut  # heure de début du premier créneau
                            max_equipe = creneaux_temp_du_jour[-1].heure_fin  # heure de fin du dernier créneau
                        else:
                            if min_equipe > creneaux_temp_du_jour[0].heure_debut:  # nouveau min
                                min_equipe = creneaux_temp_du_jour[0].heure_debut
                            if max_equipe < creneaux_temp_du_jour[-1].heure_fin:  # nouveau max
                                max_equipe = creneaux_temp_du_jour[-1].heure_fin

                creneaux_travailles = equipe.of_creneau_ids
                for i in range(1,8):
                    creneaux_du_jour = creneaux_travailles.filtered(lambda x: x.jour_number == i)
                    if len(creneaux_du_jour) == 0:
                        continue
                    if min_equipe == False:  # ==False pour éviter un éventuel 0.0 oublié
                        min_equipe = creneaux_du_jour[0].heure_debut  # heure de début du premier créneau
                        max_equipe = creneaux_du_jour[-1].heure_fin  # heure de fin du dernier créneau
                    else:
                        if min_equipe > creneaux_du_jour[0].heure_debut:  # nouveau min
                            min_equipe = creneaux_du_jour[0].heure_debut
                        if max_equipe < creneaux_du_jour[-1].heure_fin:  # nouveau max
                            max_equipe = creneaux_du_jour[-1].heure_fin
            date_min_dt = datetime.combine(today_da, datetime.min.time()) + timedelta(hours=min_equipe)  # datetime naive
            date_min_dt = tz.localize(date_min_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc
            flo_min = round(date_min_dt.hour + date_min_dt.minute / 60.0 + date_min_dt.second / 3600.0, 5)  # mintime utc as float
            if min_time == False:
                min_time = flo_min
            elif flo_min < min_time:
                min_time = flo_min
            date_max_dt = datetime.combine(today_da, datetime.min.time()) + timedelta(hours=max_equipe)  # datetime naive
            date_max_dt = tz.localize(date_max_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc
            flo_max = round(date_max_dt.hour + date_max_dt.minute / 60.0 + date_max_dt.second / 3600.0, 5)  # maxtime utc as float
            if max_time == False:
                max_time = flo_max
            elif flo_max > max_time:
                max_time = flo_max"""
        return (min_time or 3.0, max_time or 21.0)

    @api.multi
    def write(self, vals):
        res = super(HREmployee, self).write(vals)
        #self.get_archive_list_segments_temp()
        if vals.get("of_creneau_ids", False) or vals.get("of_hor_md", False) or vals.get("of_hor_mf", False) or \
           vals.get("of_hor_ad", False) or vals.get("of_hor_af", False) or vals.get("of_mode_horaires", False) or \
           vals.get("of_jour_ids", False):
            self.archiver_horaires()
        if vals.get("of_creneau_temp_start", False) or vals.get("of_creneau_temp_stop", False):
            self.archiver_horaires_temp()
        user_ids = self.mapped('user_id')
        if vals.get("of_color_ft", False) and not vals.get("no_rebounce", False):
            user_ids.write({'of_color_ft': vals.get("of_color_ft", False), 'no_rebounce': True})
        if vals.get("of_color_bg", False) and not vals.get("no_rebounce", False):
            user_ids.write({'of_color_bg': vals.get("of_color_bg", False), 'no_rebounce': True})
        return res

    @api.model
    def create(self, vals):
        employee = super(HREmployee, self).create(vals)
        if vals.get("of_creneau_ids", False) or vals.get("of_hor_md", False) or vals.get("of_hor_mf", False) or \
           vals.get("of_hor_ad", False) or vals.get("of_hor_af", False) or vals.get("of_mode_horaires", False) or \
           vals.get("of_jour_ids", False):
            self.archiver_horaires()
        if vals.get("of_creneau_temp_start", False) or vals.get("of_creneau_temp_stop", False):
            self.archiver_horaires_temp()
        if employee.user_id:
            employee.user_id.write({
                'of_color_ft': employee.of_color_ft,
                'of_color_bg': employee.of_color_bg,
                'no_rebounce': True,
                })
        return employee


class OFHorairesCreneau(models.Model):
    _name = "of.horaires.creneau"
    _order = "jour_number, heure_debut"

    """@api.model
    def _auto_init(self):
        déjà perdu du temp la-dessus... à voir si initialisation par import?
        "" "
        Initialisation des créneaux horaires en fonction des équipe et des employés
        "" "
        res = super(OFHorairesCreneau, self)._auto_init()
        set_value = False
        cr = self._cr
        cr.execute("SELECT id FROM of_horaires_creneau LIMIT 1")
        creneau_existe = bool(cr.fetchall())  # Il y a déjà au moins un créneau dans la base, pas besoin d'initialiser les créneaux
        if not creneau_existe:
            set_value = True
        
        if set_value:
            cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % ("of_planning_equipe",))
            equipe_existe = bool(cr.fetchall())  # les équipes existent! on peut aller y chercher les horaires

            
            employees = self.env['hr.employee'].search([])
            jours = self.env['of.jours'].search([('numero', '<', 7)])
            creneau_obj = self.env['of.horaires.creneau']
            if equipe_existe:
                auto_init_equipe = self.env['of.planning.equipe']._auto_init()
                equipes = self.env['of.planning.equipe'].search([])
                for equipe in equipes:
                    # des horaires du matin
                    hor_md = equipe.hor_md
                    hor_mf = equipe.hor_mf
                    hor_ad = equipe.hor_ad
                    hor_af = equipe.hor_af
                    if hor_md and hor_mf and hor_md < horaire_mf:
                        if len(creneau_obj.search([('heure_debut', '=', hor_md), ('heure_fin', '=', hor_mf)], limit=1)) == 0:  # ce créneau n'existe pas encore
                            for jour in jours:
                                vals = {
                                    'jour_id': jour.id,
                                    'heure_debut': hor_md,
                                    'heure_fin': hor_mf,
                                }
                                creneau_obj.create(vals)
                    if hor_ad and hor_af and hor_ad < horaire_af:
                        if len(creneau_obj.search([('heure_debut', '=', hor_ad), ('heure_fin', '=', hor_af)], limit=1)) == 0:  # ce créneau n'existe pas encore
                            for jour in jours:
                                vals = {
                                    'jour_id': jour.id,
                                    'heure_debut': hor_md,
                                    'heure_fin': hor_mf,
                                }
                                creneau_obj.create(vals)
            for employee in employees:
                # des horaires du matin
                hor_md = employee.of_hor_md
                hor_mf = employee.of_hor_mf
                hor_ad = employee.of_hor_ad
                hor_af = employee.of_hor_af
                if hor_md and hor_mf and hor_md < horaire_mf:
                    if len(creneau_obj.search([('heure_debut', '=', hor_md), ('heure_fin', '=', hor_mf)], limit=1)) == 0:  # ce créneau n'existe pas encore
                        for jour in jours:
                            vals = {
                                'jour_id': jour.id,
                                'heure_debut': hor_md,
                                'heure_fin': hor_mf,
                            }
                            creneau_obj.create(vals)
                if hor_ad and hor_af and hor_ad < horaire_af:
                    if len(creneau_obj.search([('heure_debut', '=', hor_ad), ('heure_fin', '=', hor_af)], limit=1)) == 0:  # ce créneau n'existe pas encore
                        for jour in jours:
                            vals = {
                                'jour_id': jour.id,
                                'heure_debut': hor_md,
                                'heure_fin': hor_mf,
                            }
                            creneau_obj.create(vals)

        return res"""

    name = fields.Char("Créneau", compute="_compute_name", store=True)
    jour_id = fields.Many2one("of.jours", string="Jour", required=True)
    jour_number = fields.Integer(related="jour_id.numero", store=True)
    heure_debut = fields.Float(string=u"Heure de début", required=True)
    heure_fin = fields.Float(string=u"Heure de fin", required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Oups! on dirait que ce créneau existe déjà...'),
        ('heure_debut_fin_constraint', 'CHECK ( heure_debut <= heure_fin )', _(u"L'Heure de début doit être antérieure à l'heure de fin")),
        ('heures_sont_des_heures_constraint', 'CHECK ( heure_debut <= 24 AND heure_debut >= 0 AND heure_fin <= 24 AND heure_fin >= 0)', _(u"Les horaires doivent se trouver entre 0 et 24"))
    ]

    @api.multi
    @api.depends("jour_id", "heure_debut", "heure_fin")
    def _compute_name(self):
        for creneau in self:
            creneau.name = (creneau.jour_id and creneau.jour_id.abr + ' ' or '') + ' - '.join(hours_to_strs(creneau.heure_debut, creneau.heure_fin))


class OFHorairesProfil(models.Model):
    _name = "of.horaires.profil"

    name = fields.Char("Nom du profil")
    of_creneau_ids = fields.Many2many("of.horaires.creneau", "profil_creneaux", "of_profil_id", "creneau_id", string=u"Créneaux")
    active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Oups! on dirait qu\'un autre profil porte déjà ce nom...'),
    ]


class OFUsers(models.Model):
    _inherit = 'res.users'

    of_color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0", oldname="color_bg")

    @api.multi
    def write(self, vals):
        res = super(OFUsers, self).write(vals)
        employees = self.mapped('employee_ids')
        if vals.get('of_color_ft', False) and not vals.get("no_rebounce", False):
            employees.write({'of_color_ft': vals.get('of_color_ft', False), 'no_rebounce': True})
        if vals.get('of_color_bg', False) and not vals.get("no_rebounce", False):
            employees.write({'of_color_bg': vals.get('of_color_bg', False), 'no_rebounce': True})
        if vals.get('tz', False) and not vals.get("no_rebounce", False):
            employees.write({'of_tz': vals.get('tz', False)})
        return res

    @api.model
    def create(self, vals):
        user = super(OFUsers, self).create(vals)
        if user.employee_ids:
            user.employee_ids.write({
                'of_color_ft': user.of_color_ft,
                'of_color_bg': user.of_color_bg,
                'no_rebounce': True,
                })
        #création automatique employee sur création utilisateur?


class OFPartners(models.Model):
    _inherit = 'res.partner'

    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_colors", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_colors", oldname="color_bg")

    @api.depends("user_ids")
    def _compute_colors(self):
        for partner in self:
            if partner.user_ids:
                partner.of_color_ft = partner.user_ids[0].of_color_ft
                partner.of_color_bg = partner.user_ids[0].of_color_bg
            else:
                partner.of_color_ft = "#0D0D0D"
                partner.of_color_bg = "#F0F0F0"


class OFMeetingType(models.Model):
    _inherit = 'calendar.event.type'

    active = fields.Boolean("Actif", default=True)


class OFMeeting(models.Model):
    _inherit = "calendar.event"

    # redefinition
    description = fields.Html('Description', states={'done': [('readonly', True)]})
    location = fields.Char('Location', compute="_compute_location", store=True, track_visibility='onchange', help="Location of Event")

    of_lieu = fields.Selection([
        ("onsite", "Dans les locaux"),
        ("phone", "Au téléphone"),
        ("offsite", "À l'exterieur"),
        ("custom", "Adresse manuelle"),
        ], string="Lieu du RDV", required=True, default="onsite")
    #user_company_ids = fields.Many2many('res.company', 'calendar_user_company_rel', 'calendar_id', 'company_id', u"sociétés du propriétaire",compute="_compute_user_company_ids")#,store=True)#related="user_id.company_ids", readonly=True)
    # tentative de domain ratée
    of_lieu_company_id = fields.Many2one("res.company", string="(Précisez)")  #,domain="[('id', 'in', user_company_ids and user_company_ids._ids)]")
    of_lieu_rdv_id = fields.Many2one("res.partner", string="(Précisez)")
    of_lieu_address_street = fields.Char(string="Rue")  # , compute="_compute_geo")
    of_lieu_address_street2 = fields.Char(string="Rue (2)")  # , compute="_compute_geo")
    of_lieu_address_city = fields.Char(string="Ville")  # , compute="_compute_geo")
    of_lieu_address_state_id = fields.Many2one("res.country.state", string=u"Région")  # , compute="_compute_geo")
    of_lieu_address_zip = fields.Char(string="Code postal")  # , compute="_compute_geo")
    of_lieu_address_country_id = fields.Many2one("res.country", string="Pays")  # , compute="_compute_geo")
    of_on_phone = fields.Boolean(u'Au téléphone', compute="_compute_on_phone")
    of_color_partner_id = fields.Many2one("res.partner", "Partner whose color we will take", compute='_compute_color_partner', store=False)
    of_geo_lat = fields.Float(string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", compute="_compute_geo", store=False, search='_search_lat')
    of_geo_lng = fields.Float(string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", compute="_compute_geo", store=False, search='_search_lng')
    of_precision = fields.Selection([
        ('manual', "Manuel"),
        ('high', "Haut"),
        ('medium', "Moyen"),
        ('low', "Bas"),
        ('no_address', u"--"),
        ('unknown', u"Indéterminé"),
        ('not_tried', u"Pas tenté"),
        ], default='no_address', help=u"Niveau de précision de la géolocalisation", compute="_compute_geo", store=False, search='_search_precision')

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

    @api.multi
    @api.depends("of_lieu")
    def _compute_on_phone(self):
        for meeting in self:
            if meeting.of_lieu and meeting.of_lieu == "phone":
                meeting.of_on_phone = True

    @api.multi
    @api.depends("of_lieu", "of_lieu_company_id", "of_lieu_rdv_id")
    def _compute_geo(self):
        for meeting in self:
            if meeting.of_lieu and meeting.of_lieu == "onsite":  # dans les locaux
                vals = {
                    "of_lieu_address_street": meeting.of_lieu_company_id.street,
                    "of_lieu_address_street2": meeting.of_lieu_company_id.street2,
                    "of_lieu_address_city": meeting.of_lieu_company_id.city,
                    "of_lieu_address_state_id": meeting.of_lieu_company_id.state_id.id,
                    "of_lieu_address_zip": meeting.of_lieu_company_id.zip,
                    "of_lieu_address_country_id": meeting.of_lieu_company_id.country_id.id,
                    'of_geo_lat': meeting.of_lieu_company_id.geo_lat,
                    'of_geo_lng': meeting.of_lieu_company_id.geo_lng,
                    'of_precision': meeting.of_lieu_company_id.precision,
                }
            elif meeting.of_lieu and meeting.of_lieu == "offsite":  # a l'exterieur
                vals = {
                    "of_lieu_address_street": meeting.of_lieu_rdv_id.street,
                    "of_lieu_address_street2": meeting.of_lieu_rdv_id.street2,
                    "of_lieu_address_city": meeting.of_lieu_rdv_id.city,
                    "of_lieu_address_state_id": meeting.of_lieu_rdv_id.state_id.id,
                    "of_lieu_address_zip": meeting.of_lieu_rdv_id.zip,
                    "of_lieu_address_country_id": meeting.of_lieu_rdv_id.country_id.id,
                    'of_geo_lat': meeting.of_lieu_rdv_id.geo_lat,
                    'of_geo_lng': meeting.of_lieu_rdv_id.geo_lng,
                    'of_precision': meeting.of_lieu_rdv_id.precision,
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

    @api.multi
    @api.depends("of_lieu", "of_lieu_company_id", "of_lieu_rdv_id", "of_precision", "of_lieu_address_street", "of_lieu_address_street2",
                 "of_lieu_address_city", "of_lieu_address_state_id", "of_lieu_address_zip", "of_lieu_address_country_id")
    def _compute_location(self):
        for meeting in self:
            if meeting.of_precision != "no_address":
                le_tab = []
                le_texte = ""
                """
                On remplit le tableau puis on crée le texte
                """
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

    """tentative de domain ratée
    @api.multi
    @api.depends("user_id.company_ids")
    def _compute_user_company_ids(self):
        for meeting in self:
            la_list = []
            #meeting.user_company_ids = [(5,0,0)] + [(4,le_id,False) for le_id in meeting.user_id.company_ids._ids]
            if meeting.user_id.id:
                company_ids = meeting.user_id.company_ids
                la_list = [x.id for x in company_ids]
            meeting.user_company_ids = [(6,0,la_list)]"""

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

    """
    These fields would be necessary if use_contacts="0" in <calendar>. See event_data_transforgit statuism function in .js file

    of_color_ft = fields.Char(string="Couleur de texte", help="Couleur de texte de l'utilisateur", compute="_compute_of_color")
    of_color_bg = fields.Char(string="Couleur de fond", help="Couleur de fond de l'utilisateur", compute="_compute_of_color")

    @api.multi
    @api.depends('of_color_partner_id')
    def _compute_of_color(self):
        for meeting in self:
            meeting.of_color_bg = meeting.of_color_partner_id.of_color_bg
            meeting.of_color_ft = meeting.of_color_partner_id.of_color_ft
    """

    @api.multi
    @api.depends('user_id')
    def _compute_color_partner(self):
        for meeting in self:
            if meeting.user_id.partner_id in meeting.partner_ids:
                meeting.color_partner_id = meeting.user_id.partner_id
            else:
                meeting.color_partner_id = (filter(lambda partner: partner.user_ids, meeting.partner_ids) or [False])[0]

    @api.multi
    def write(self, vals):
        if vals.get('of_lieu_rdv_id', False) or vals.get('of_lieu_company_id', False):
            le_lieu = vals.get('of_lieu', False)
            if not le_lieu:
                le_lieu = self.env["calendar.event"].browse(self._ids[0]).of_lieu
            if le_lieu == "onsite":
                la_company = self.env["res.company"].browse(vals.get("of_lieu_company_id", False))
                vals["of_lieu_address_street"] = la_company.partner_id.street
                vals["of_lieu_address_street2"] = la_company.partner_id.street2
                vals["of_lieu_address_city"] = la_company.partner_id.city
                vals["of_lieu_address_state_id"] = la_company.partner_id.state_id.id
                vals["of_lieu_address_zip"] = la_company.partner_id.zip
                vals["of_lieu_address_country_id"] = la_company.partner_id.country_id.id
            elif le_lieu == "offsite":
                le_partner = self.env["res.partner"].browse(vals.get("of_lieu_rdv_id"))
                vals["of_lieu_address_street"] = le_partner.street
                vals["of_lieu_address_street2"] = le_partner.street2
                vals["of_lieu_address_city"] = le_partner.city
                vals["of_lieu_address_state_id"] = le_partner.state_id.id
                vals["of_lieu_address_zip"] = le_partner.zip
                vals["of_lieu_address_country_id"] = le_partner.country_id.id
            elif le_lieu == "phone":
                vals["of_lieu_address_street"] = False
                vals["of_lieu_address_street2"] = False
                vals["of_lieu_address_city"] = False
                vals["of_lieu_address_state_id"] = False
                vals["of_lieu_address_zip"] = False
                vals["of_lieu_address_country_id"] = False
                vals["of_geo_lat"] = False
                vals["of_geo_lng"] = False
                vals["of_precision"] = "no_address"
        return super(OFMeeting, self).write(vals)

    @api.model
    def create(self, vals):
        """
        En cas de création par google agenda, le champs "location" peut etre renseigné, or dans ce module on transforme ce champ en champ calculé
        """
        le_lieu = vals.get('of_lieu', False)
        if not le_lieu:
            vals["of_lieu"] = "custom"
        else:
            if le_lieu == "onsite":
                la_company = self.env["res.company"].browse(vals.get("of_lieu_company_id"))
                vals["of_lieu_address_street"] = la_company.partner_id.street
                vals["of_lieu_address_street2"] = la_company.partner_id.street2
                vals["of_lieu_address_city"] = la_company.partner_id.city
                vals["of_lieu_address_state_id"] = la_company.partner_id.state_id.id
                vals["of_lieu_address_zip"] = la_company.partner_id.zip
                vals["of_lieu_address_country_id"] = la_company.partner_id.country_id.id
            elif le_lieu == "offsite":
                le_partner = self.env["res.partner"].browse(vals.get("of_lieu_rdv_id"))
                vals["of_lieu_address_street"] = le_partner.street
                vals["of_lieu_address_street2"] = le_partner.street2
                vals["of_lieu_address_city"] = le_partner.city
                vals["of_lieu_address_state_id"] = le_partner.state_id.id
                vals["of_lieu_address_zip"] = le_partner.zip
                vals["of_lieu_address_country_id"] = le_partner.country_id.id
            elif le_lieu == "phone":
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
        return super(OFMeeting, self).create(vals)


class OFCalendarMixin(models.AbstractModel):
    _name = "of.calendar.mixin"

    state_int = fields.Integer(string="Valeur d'état", compute="_compute_state_int", help="valeur allant de 0 à 3 inclus")

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


class OFCalendarAttendeeMixin(models.AbstractModel):
    _name = "of.calendar.attendee.mixin"

    @api.model
    def get_working_hours_fields(self):
        """
        Returns a dictionnary with 4 properties: morning_start, morning_end, afternoon_start, afternoon_end
        these properties have names of corresponding fields as values
        """
        raise NotImplementedError("A class inheriting from this one must implement a 'get_state_int_map' function")
