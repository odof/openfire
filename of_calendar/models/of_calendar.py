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

def se_chevauchent(debut_1, fin_1, debut_2, fin_2, strict=False):
    """renvoi True si les horaires se chevauchent, False sinon."""
    if not strict:
        debut_1 < fin_2 and debut_2 < fin_1
    return debut_1 <= fin_2 and debut_2 <= fin_1

@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

def jour_abr_2_nb(str):
    res = str.replace(u'"lun."', u"1")
    res = res.replace(u'"mar."', u"2")
    res = res.replace(u'"mer."', u"3")
    res = res.replace(u'"jeu."', u"4")
    res = res.replace(u'"ven."', u"5")
    res = res.replace(u'"sam."', u"6")
    res = res.replace(u'"dim."', u"7")
    return res

class HREmployee(models.Model):
    _inherit = "hr.employee"

    def _default_tz(self):
        return self.env.user.tz or 'Europe/Paris'

    @api.depends('tz')
    def _compute_tz_offset(self):
        for employee in self:
            employee.tz_offset = datetime.now(pytz.timezone(employee.tz or 'GMT')).strftime('%z')

    @api.multi
    def check_no_overlapping(self):
        for employee in self:
            for i in range(1,8):
                creneaux_du_jour = employee.creneau_ids.filtered(lambda x: x.jour_number == i)
                la_len = len(creneaux_du_jour)
                for j in range(la_len):
                    for k in range(j+1, la_len):
                        d1 = creneaux_du_jour[j].heure_debut
                        f1 = creneaux_du_jour[j].heure_fin
                        d2 = creneaux_du_jour[k].heure_debut
                        f2 = creneaux_du_jour[k].heure_fin
                        if se_chevauchent(d1, f1, d2, f2):
                            #raise UserError(u"Oups! Des créneaux se chevauchent")
                            return False
                creneaux_temp_du_jour = employee.creneau_temp_ids.filtered(lambda jour: jour.jour_number == i)
                la_len = len(creneaux_temp_du_jour)
                for j in range(la_len):
                    for k in range(j+1, la_len):
                        d1 = creneaux_temp_du_jour[j].heure_debut
                        f1 = creneaux_temp_du_jour[j].heure_fin
                        d2 = creneaux_temp_du_jour[k].heure_debut
                        f2 = creneaux_temp_du_jour[k].heure_fin
                        if se_chevauchent(d1, f1, d2, f2):
                            #raise UserError(u"Oups! Des créneaux se chevauchent")
                            return False
        return True

    tz = fields.Selection(
        _tz_get, string='Fuseau horaire', required=True, default=lambda self: self._default_tz(),
        help="Le fuseau horaire de l'équipe d'intervention")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)
    u"""Création horaires avancés"""
    mode_horaires = fields.Selection([
        ("easy","Facile"),
        ("advanced",u"Avancé")], string="Mode de Sélection des horaires", required=True, default="easy")
    profil_id = fields.Many2one("of.horaires.profil", "Profil")
    creneau_ids = fields.Many2many("of.horaires.creneau", "employee_creneaux", "employee_id", "creneau_id", string=u"Créneaux", order="jour_number, heure_debut")
    creneau_temp_ids = fields.Many2many("of.horaires.creneau", "employee_creneaux_temp", "employee_id", "creneau_id", string=u"Créneaux", order="jour_number, heure_debut")
    creneau_temp_start = fields.Date(string=u"Début des horaires temporaires")
    creneau_temp_stop = fields.Date(string="Fin des horaires temporaires")
    archive_horaires = fields.Text(string="Archive des horaires")
    archive_horaires_temp = fields.Text(string="Archive des horaires temporaires")

    _sql_constraints = [
        ('creneau_temp_start_stop_constraint', 'CHECK ( creneau_temp_start <= creneau_temp_stop )', _(u"La date de début de validité doit être antérieure ou égale à celle de fin")),
    ]

    _constraints = [
        (check_no_overlapping, u'Vous ne pourrez pas sauvegarder tant que des créneaux se chevauchent!', []),
    ]

    @api.onchange("creneau_ids","creneau_temp_ids")
    def _onchange_creneaux(self):
        if not self.check_no_overlapping():
            raise UserError(u"Oups! Des créneaux se chevauchent. Veuillez vous assurer que ce ne soit plus le cas avant de sauvegarder.")

    @api.onchange("creneau_temp_start")
    def _onchange_creneau_temp_start(self):
        self.ensure_one()
        if self.creneau_temp_start:
            date_deb = fields.Date.from_string(self.creneau_temp_start)
            date_fin = date_deb + timedelta(days=6)
            self.creneau_temp_stop = fields.Date.to_string(date_fin)

    @api.multi
    def possede_creneau(self,creneau_id):
        u"""vérifie que tous les employés présents dans self possèdent tel ou tel créneau.
            Ne prend pas en compte les créneaux temporaires."""
        if len(self._ids) == 0:
            return None
        for employee in self:
            if len(employee.creneau_ids.filtered(lambda x: x.id == creneau_id)) > 0:
                continue
            else:
                return False
        return True

    @api.multi
    def archiver_horaires(self):
        str_date_today = fields.Date.today()
        d_date_today = fields.Date.from_string(str_date_today)
        un_jour = timedelta(days=1)
        for employee in self:
            """Récupérer l'archive actuelle, si la date d'aujourd'hui existe déjà dans l'archive, on la remplace"""
            archive = employee.archive_horaires
            if archive:
                les_morceaux = archive.split(u"\n")
                for le_morceau in les_morceaux:
                    str_la_date = le_morceau[2:12]  # la date commence au 3eme caractère
                    if str_date_today == str_la_date:
                        les_morceaux.remove(le_morceau)
                        break
            else:
                les_morceaux = []
            """Ajout date d'hier si besoin"""
            if len(les_morceaux) > 0:
                le_morceau = les_morceaux[-1]
                if le_morceau[15] == u'f':  # le dernier morceau de la liste n'a pas de date de fin.
                    d_date_hier = d_date_today - un_jour
                    str_date_hier = fields.Date.to_string(d_date_hier)
                    les_morceaux[-1] = le_morceau[:15] + u'"' + str_date_hier + u'"' + le_morceau[20:]
            """création de l'archive"""
            dict_nouveau_morceau = {}  # dict contenant les horaires de travail
            if employee.mode_horaires == u"advanced":  # mode avancé
                for creneau in employee.creneau_ids:
                    if creneau.jour_id.abr not in dict_nouveau_morceau:
                        dict_nouveau_morceau[creneau.jour_id.abr] = []
                    dict_nouveau_morceau[creneau.jour_id.abr].append((creneau.heure_debut, creneau.heure_fin))
            #else:  # mode facile -> a faire quand rebase avec code rdvcom
            if archive:
                str_nouveau_morceau = u'["%s", false, %s]' % (str_date_today, json.dumps(dict_nouveau_morceau))
            else:  # lors de la permière création d'horaires, on considère que l'employé avait ces horaires depuis sa création
                str_nouveau_morceau = u'["%s", false, %s]' % (employee.create_date[:10], json.dumps(dict_nouveau_morceau))
            les_morceaux.append(str_nouveau_morceau)
            nouvelle_archive = u"\n".join(les_morceaux)
            employee.archive_horaires = nouvelle_archive


    @api.multi
    def archiver_horaires_temp(self):
        for employee in self:
            archive = employee.archive_horaires_temp
            if archive:
                les_morceaux = archive.split("\n")
                """Vérification qu'il n'y a pas de chevauchement avec des dates d'horaires temporaires existants"""
                for le_morceau in les_morceaux:
                    la_liste = json.loads(le_morceau)
                    if se_chevauchent(la_liste[0], la_liste[1], employee.creneau_temp_start, employee.creneau_temp_stop, True):
                        raise UserError(u"OH oh! le système nous dit qu'il y a du chevauchement au niveau de l'archive des horaires temporaires.\n"
                                        u"Pour que tout se passe bien, veuillez sélectionner des dates de début et de fin qui ne chevauchent pas des dates de début et de fin existantes dans l'archive.\n"
                                        u"dates source du conflit: entre le %s et le %s" % (la_liste[0], la_liste[1]))
            else:
                les_morceaux = []
            """Création du nouveau morceau et de l'archive"""
            dict_nouveau_morceau = {}  # dict contenant les horaires de travail temporaire
            for creneau in employee.creneau_temp_ids:
                if creneau.jour_id.abr not in dict_nouveau_morceau:
                    dict_nouveau_morceau[creneau.jour_id.abr] = []
                dict_nouveau_morceau[creneau.jour_id.abr].append((creneau.heure_debut, creneau.heure_fin))
            str_nouveau_morceau = u'["%s", "%s", %s]' % (employee.creneau_temp_start, employee.creneau_temp_stop, json.dumps(dict_nouveau_morceau))
            les_morceaux.append(str_nouveau_morceau)
            les_morceaux.sort(key=lambda x: x[2:12])  # si quelqu'un ajoute des horaires temporaires antérieurs à ceux déjà ajouté, BIM FOOLPROOF
            nouvelle_archive = u"\n".join(les_morceaux)
            employee.archive_horaires_temp = nouvelle_archive

    @api.multi
    def get_archive_list_horaires(self, jour_keys="number"):
        """Renvois l'archive des horaires des employés présents dans self sous forme de liste
        résultat sous forme [ [date_debut, date_fin, dict_horaires], ...]"""
        res = {}
        un_jour = timedelta(days=1)
        for employee in self:
            res[employee.id] = {}
            if not employee.archive_horaires:
                continue
            str_archive = u'[%s]' % employee.archive_horaires.replace(u"\n", u",")
            if jour_keys == "number":
                str_archive = jour_abr_2_nb(str_archive)
            list_archive = json.loads(str_archive)
            res[employee.id] = list_archive
        return res

    @api.multi
    def get_archive_list_horaires_temp(self, jour_keys="number"):
        """Renvois l'archive des horaires temporaires des employés présents dans self sous forme de liste
        résultat sous forme [ [date_debut, date_fin, dict_horaires], ...]"""
        res = {}
        un_jour = timedelta(days=1)
        for employee in self:
            res[employee.id] = {}
            if not employee.archive_horaires_temp:
                continue
            str_archive = u'[%s]' % employee.archive_horaires_temp.replace(u"\n", u",")
            if jour_keys == "number":
                str_archive = jour_abr_2_nb(str_archive)
            list_archive = json.loads(str_archive)
            res[employee.id] = list_archive
        return res

    @api.model
    def get_list_horaires(self, employee_ids, date_start, date_stop):
        # transformer date_start et date_stop en date locale
        dt_date_start_naive = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")  # datetime naif
        dt_date_start_utc = pytz.utc.localize(dt_date_start_naive, is_dst=None)  # datetime utc
        dt_date_stop_naive = datetime.strptime(date_stop, "%Y-%m-%d %H:%M:%S")  # datetime naif
        dt_date_stop_utc = pytz.utc.localize(dt_date_stop_naive, is_dst=None)  # datetime utc
        un_jour = timedelta(days=1)

        res = {}
        compare_precision = 5
        archive_list_horaires = self.browse(employee_ids).get_archive_list_horaires()
        archive_list_horaires_temp = self.browse(employee_ids).get_archive_list_horaires_temp()
        for employee in self.browse(employee_ids):
            res[employee.id] = []
            # en cas d'employés sur différentes timezones
            tz = pytz.timezone(employee.tz or "Europe/Paris")
            dt_date_start_local = dt_date_start_utc.astimezone(tz)  # datetime local
            dt_date_stop_local = dt_date_stop_utc.astimezone(tz)  # datetime local
            str_d_date_start = fields.Date.to_string(dt_date_start_local).decode('utf-8')
            str_d_date_stop = fields.Date.to_string(dt_date_stop_local).decode('utf-8')

            # on récupère les horaires standards
            horaires_employee = archive_list_horaires[employee.id]
            horaires_utiles = []
            if len(horaires_employee) == 1:  # les seuls horaires standard connu, on considère qu'ils sont valable sur la periode demandée
                horaires_utiles.append([str_d_date_start, str_d_date_stop, horaires_employee[0][2]])
            elif len(horaires_employee) > 1:
                # on cherche les index de début et de fin
                index_start = -1
                index_stop = -1
                for i in range(len(horaires_employee)):

                    if index_start == -1:  # n'a pas été affecté
                        if not horaires_employee[i][1]:
                            index_start = index_stop = i
                        elif se_chevauchent(str_d_date_start, str_d_date_start, horaires_employee[i][0], horaires_employee[i][1], True):
                            index_start = i
                    if index_stop == -1:  # n'a pas été affecté
                        if not horaires_employee[i][1]:
                            index_stop = i
                        elif se_chevauchent(str_d_date_stop, str_d_date_stop, horaires_employee[i][0], horaires_employee[i][1], True):
                            index_stop = i
                    if index_start != -1 and index_stop != -1:  # on a trouvé les 2 indexes
                        break

                if index_start == index_stop:  # on a de la chance! l'employé n'a pas changé d'horaires entre les 2 dates demandées
                    horaires_utiles.append([str_d_date_start, str_d_date_stop, horaires_employee[index_start][2]])
                else:  # mince alors! l'employé a changé d'horaires entre les 2 dates demandées
                    horaires_utiles.append([str_d_date_start, horaires_employee[index_start][1], horaires_employee[index_start][2]])
                    for i in range(index_start + 1, index_stop):
                        horaires_utiles.append([horaires_employee[i][0], horaires_employee[i][1], horaires_employee[i][2]])
                    horaires_utiles.append([horaires_employee[index_stop][0], str_d_date_stop, horaires_employee[index_stop][2]])
            # On a la liste des horaires standards! \o/ maintenant on récupère si besoin la liste des horaires temporaires
            horaires_employee_temp = archive_list_horaires_temp[employee.id]
            horaires_temp_utiles = []
            if len(horaires_employee_temp) == 0:  # oups! pas d'horaires temporaires
                continue
            # Sélection des horaires temporaires concernés
            for i in range(len(horaires_employee_temp)):
                if se_chevauchent(str_d_date_start, str_d_date_stop, horaires_employee_temp[i][0], horaires_employee_temp[i][1], True):
                    # chevauchement! ce créneau est à prendre en compte
                    if (horaires_employee_temp[i][0] < str_d_date_start):  # on coupe ce qui dépasse
                        horaires_employee_temp[i][0] = str_d_date_start
                    if (horaires_employee_temp[i][1] > str_d_date_stop):  # à gauche et à droite
                        horaires_employee_temp[i][1] = str_d_date_stop
                    horaires_temp_utiles.append(horaires_employee_temp[i])
            # OK! on a 2 listes de segments d'horaires sur un même intervalle, fiou!
            # FUUUUUUU-ZION!
            index_courant = 0
            while len(horaires_temp_utiles) > 0:
                segment_std = horaires_utiles[index_courant]
                segment_temp = horaires_temp_utiles.pop(0)
                while not se_chevauchent(segment_temp[0], segment_temp[1], segment_std[0], segment_std[1], True):
                    res[employee.id].append(horaires_utiles[index_courant])
                    index_courant += 1
                    segment_std = horaires_utiles[index_courant]

                d_debut_temp = fields.Date.from_string(segment_temp[0])
                d_debut_temp -= un_jour
                str_debut_temp = fields.Date.to_string(d_debut_temp).decode('utf-8')
                d_fin_temp = fields.Date.from_string(segment_temp[1])
                d_fin_temp += un_jour
                str_fin_temp = fields.Date.to_string(d_fin_temp).decode('utf-8')
                sous_seg_1 = deepcopy(segment_std)
                sous_seg_1[1] = str_debut_temp
                if segment_temp[1] <= segment_std[1]:
                    # le segment d'horaires temporaires est inclus dans le segment d'horaires standards
                    # un sous-segment a été créé, on modifie le segment courant
                    horaires_utiles[index_courant][0] = str_fin_temp
                    if horaires_utiles[index_courant][0] > horaires_utiles[index_courant][1]:
                        index_courant += 1
                else:  # le segment d'horaires temporaires chevauche 2 segments d'horaires standards
                    # on met à jour le prochain segment d'horaires standards
                    index_courant += 1
                    horaires_utiles[index_courant][0] = str_fin_temp

                if sous_seg_1[0] <= sous_seg_1[1]:  # est un vrai segment, on l'ajoute!
                    res[employee.id].append(sous_seg_1)
                res[employee.id].append(segment_temp)
            if index_courant < index_stop:
                for j in range(index_courant, index_stop + 1):
                    segment_std = horaires_utiles[j]
                    res[employee.id].append(segment_std)

        # WHOO HOO on y est! \o/
        # le résultat est un dictionnaire avec les identifiants des employés en clés
        # les valeurs sont de la forme [ [debut, fin, horaires] ,  [debut, fin, horaires] ,  ... ]
        # avec un seul choix d'horaires possibles pour une date donnée
        return res

    @api.multi
    def write(self, vals):
        res = super(HREmployee, self).write(vals)
        #self.get_archive_list_horaires_temp()
        if vals.get("creneau_ids", False):
            self.archiver_horaires()
        if vals.get("creneau_temp_start", False) or vals.get("creneau_temp_stop", False):
            self.archiver_horaires_temp()
        a_ver = self.env['hr.employee'].get_list_horaires([7], "2019-08-01 00:00:00", "2019-08-31 23:59:59")
        return res

    @api.model
    def create(self, vals):
        employee = super(HREmployee, self).create(vals)
        if vals.get("creneau_ids", False):
            employee.archiver_horaires()
        return employee

class OFHorairesCreneau(models.Model):
    _name = "of.horaires.creneau"
    _order = "jour_number, heure_debut"

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
    @api.depends("jour_id","heure_debut","heure_fin")
    def _compute_name(self):
        for creneau in self:
            creneau.name = (creneau.jour_id and creneau.jour_id.abr + ' ' or '') + ' - '.join(hours_to_strs(creneau.heure_debut, creneau.heure_fin))

class OFHorairesProfil(models.Model):
    _name = "of.horaires.profil"

    name = fields.Char("Nom du profil")
    creneau_ids = fields.Many2many("of.horaires.creneau", "profil_creneaux", "profil_id", "creneau_id", string=u"Créneaux")
    active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Oups! on dirait qu\'un autre profil porte déjà ce nom...'),
    ]

class OFUsers(models.Model):
    _inherit = 'res.users'

    of_color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0", oldname="color_bg")

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

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    of_hor_md = fields.Float(string=u'Matin début', required=True, digits=(12, 1), default=9)
    of_hor_mf = fields.Float(string='Matin fin', required=True, digits=(12, 1), default=12)
    of_hor_ad = fields.Float(string=u'Après-midi début', required=True, digits=(12, 1), default=14)
    of_hor_af = fields.Float(string=u'Après-midi fin', required=True, digits=(12, 1), default=18)
    of_jour_ids = fields.Many2many('of.jours', 'employee_jours_rel', 'employee_id', 'jour_id', string='Jours travaillés', required=True, default=_get_default_jours)
    of_tz = fields.Selection(_tz_get, string='Fuseau horaire', default=lambda self: self.env.user.tz or 'Europe/Paris', required=True,
                             help="The Team's timezone, used to output proper date and time values "
                               "inside printed reports. It is important to set a value for this field. "
                               "You should use the same timezone that is otherwise used to pick and "
                               "render date and time values: your computer's timezone.")
    of_tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset')
    of_address_depart_id = fields.Many2one('res.partner', string=u'Adresse de départ')
    of_address_retour_id = fields.Many2one('res.partner', string='Adresse de retour')

    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_colors")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_colors")

    @api.depends('of_tz')
    def _compute_tz_offset(self):
        for employee in self:
            employee.of_tz_offset = datetime.now(pytz.timezone(employee.of_tz or 'GMT')).strftime('%z')

    @api.depends("user_id")
    def _compute_colors(self):
        for employee in self:
            if employee.user_id:
                employee.of_color_ft = employee.user_id.of_color_ft
                employee.of_color_bg = employee.user_id.of_color_bg
            else:
                employee.of_color_ft = "#0D0D0D"
                employee.of_color_bg = "#F0F0F0"

    _sql_constraints = [
        ('hor_md_mf_constraint', 'CHECK ( of_hor_md <= of_hor_mf )', _(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")),
        ('hor_mf_ad_constraint', 'CHECK ( of_hor_mf <= of_hor_ad )', _(u"L'Heure de fin de matinée doit être antérieure à l'heure de début d'après-midi")),
        ('hor_ad_af_constraint', 'CHECK ( of_hor_ad <= of_hor_af )', _(u"L'Heure de début d'après-midi doit être antérieure à l'heure de fin d'après-midi")),
    ]

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
    # user_company_ids = fields.Many2many('res.company', 'calendar_user_company_rel', 'calendar_id', 'company_id', u"sociétés du propriétaire",compute="_compute_user_company_ids")#,store=True)#related="user_id.company_ids", readonly=True)
    # tentative de domain ratée
    of_lieu_company_id = fields.Many2one("res.company", string="(Précisez)")  # ,domain="[('id', 'in', user_company_ids and user_company_ids._ids)]")
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
        return [('id', 'in', self.env['calendar.event'].search(['|', '&', ('of_lieu_company_id', 'in', companies._ids),
                                                                          ('of_lieu', '=', 'onsite'),
                                                                     '&', ('of_lieu_rdv_id', 'in', partners._ids),
                                                                          ('of_lieu', '=', 'offsite')])._ids)]

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
        return [('id', 'in', self.env['calendar.event'].search(['|', '&', ('of_lieu_company_id', 'in', companies._ids),
                                                                          ('of_lieu', '=', 'onsite'),
                                                                     '&', ('of_lieu_rdv_id', 'in', partners._ids),
                                                                          ('of_lieu', '=', 'offsite')])._ids)]

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
        return [('id', 'in', self.env['calendar.event'].search(['|', '&', ('of_lieu_company_id', 'in', companies._ids),
                                                                          ('of_lieu', '=', 'onsite'),
                                                                     '&', ('of_lieu_rdv_id', 'in', partners._ids),
                                                                          ('of_lieu', '=', 'offsite')])._ids)]

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
    These fields would be necessary if use_contacts="0" in <calendar>. See event_data_transform function in .js file

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
