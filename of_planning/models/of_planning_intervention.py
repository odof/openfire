# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from __builtin__ import False

class OfPlanningTache(models.Model):
    _name = "of.planning.tache"
    _description = u"Planning OpenFire : Tâches"

    name = fields.Char(u'Libellé', size=64, required=True)
    description = fields.Text('Description')
    verr = fields.Boolean(u'Verrouillé')
    product_id = fields.Many2one('product.product', 'Produit')
    active = fields.Boolean('Actif', default=True)
    imp_detail = fields.Boolean(u'Imprimer Détail', help=u"""Impression du détail des tâches dans le planning semaine
Si cette option n'est pas cochée, seule la tâche le plus souvent effectuée dans la journée apparaîtra""", default=True)
    duree = fields.Float(u'Durée par défaut', digits=(12, 5), default=1.0)
    category_id = fields.Many2one('hr.employee.category', string=u"Catégorie d'employés")
    is_crm = fields.Boolean(u'Tâche CRM')
    equipe_ids = fields.Many2many('of.planning.equipe', 'equipe_tache_rel', 'tache_id', 'equipe_id', 'Équipes')

    @api.multi
    def unlink(self):
        if self.search([('id','in',self._ids),('verr','=',True)]):
            raise ValidationError(u'Vous essayez de supprimer une tâche verrouillée.')
        return super(OfPlanningTache, self).unlink()

class OfPlanningEquipe(models.Model):
    _name = "of.planning.equipe"
    _description = u"Équipe d'intervention"
    _order = "sequence, name"

#     def _get_employee_equipes(self, cr, uid, ids, context=None):
#         result = []
#         for emp in self.read(cr, uid, ids, ['equipe_ids']):
#             result += emp['equipe_ids']
#         return list(set(result))

    name = fields.Char(u'Équipe', size=128, required=True)
    note = fields.Text('Description')
    employee_ids = fields.Many2many('hr.employee', 'of_planning_employee_rel', 'equipe_id', 'employee_id', u'Employés')
    active = fields.Boolean('Actif', default=True)
    category_ids = fields.Many2many('hr.employee.category', 'equipe_category_rel', 'equipe_id', 'category_id', u'Catégories')
    intervention_ids = fields.One2many('of.planning.intervention', 'equipe_id', u'Interventions liées', copy=False)
    tache_ids = fields.Many2many('of.planning.tache', 'equipe_tache_rel', 'equipe_id', 'tache_id', u'Compétences')
    hor_md = fields.Float(u'Matin début', required=True, digits=(12, 5))
    hor_mf = fields.Float('Matin fin', required=True, digits=(12, 5))
    hor_ad = fields.Float(u'Après-midi début', required=True, digits=(12, 5))
    hor_af = fields.Float(u'Après-midi fin', required=True, digits=(12, 5))
    sequence = fields.Integer(u'Séquence', help=u"Ordre d'affichage (plus petit en premier)")
        

    @api.onchange('employee_ids')
    def onchange_employees(self):
        if not self.category_ids:
            category_ids = []
            for employee in self.employee_ids:
                for category in employee.category_ids:
                    if category.id not in category_ids:
                        category_ids.append(category.id)
            if category_ids:
                self.category_ids = category_ids

    @api.onchange('hor_md','hor_mf','hor_ad','hor_af')
    def onchange_horaires(self):
        hors = (self.hor_md, self.hor_mf, self.hor_ad, self.hor_af)
        if all(hors):
            for hor in hors:
                if hor > 24:
                    raise ValidationError(u"L'heure doit être inférieure ou égale à 24")
            if hors[0] > hors[1] or hors[2] > hors[3]:
                raise ValidationError(u"L'heure de début ne peut pas être supérieure à l'heure de fin")
            if(hors[1] > hors[2]):
                raise ValidationError(u"L'heure de l'après-midi ne peut pas être inférieure à l'heure du matin")

class OfPlanningInterventionRaison(models.Model):
    _name = "of.planning.intervention.raison"
    _description = u"Raisons d'intervention reportée"

    name = fields.Char(u'Libellé', size=128, required=True, select=True)

class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _description = "Planning d'intervention OpenFire"
    _inherit = "of.readgroup"

#     def _get_color(self, cr, uid, ids, *args):
#         result = {}
#         for intervention in self.browse(cr, uid, ids):
#             equipe = intervention.equipe_id
#             cal_color = equipe and equipe.color_id
#             result[intervention.id] = cal_color and (intervention.state == 'draft' and cal_color.color2 or cal_color.color) or ''
#         return result

    name = fields.Char(string=u'Libellé', required=True)
    date = fields.Datetime(string='Date intervention', required=True)
    date_deadline = fields.Datetime(string='Deadline')
    date_deadline_display = fields.Datetime(related='date_deadline', string="Date Fin")
    duree = fields.Float(string=u'Durée intervention', required=True, digits=(12, 5))
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.uid)
    partner_id = fields.Many2one('res.partner', string='Client', oldname='part_id')
    partner_city = fields.Char(related='partner_id.city')
    raison_id = fields.Many2one('of.planning.intervention.raison', string='Raison')
    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    equipe_id = fields.Many2one('of.planning.equipe', string='Équipe', required=True, oldname='poseur_id')
    employee_ids = fields.Many2many(related='equipe_id.employee_ids', string='Intervenants', readonly=True)
    state = fields.Selection([
            ('draft', 'Brouillon'),
            ('confirm', u'Confirmé'),
            ('done', u'Réalisé'),
            ('cancel', u'Annulé'),
            ('postponed', u'Reporté'),
        ], string=u'État', index=True, readonly=True, default='draft')
#     state = fields.Many2one('of.planning.intervention.state', string=u"État")
    company_id = fields.Many2one('res.company', string='Magasin', default=lambda self: self.env.user.company_id.id)
    description = fields.Text(string='Description')
    hor_md = fields.Float(string=u'Matin début', required=True, digits=(12, 5))
    hor_mf = fields.Float(string='Matin fin', required=True, digits=(12, 5))
    hor_ad = fields.Float(string=u'Après-midi début', required=True, digits=(12, 5))
    hor_af = fields.Float(string=u'Après-midi fin', required=True, digits=(12, 5))
    hor_sam = fields.Boolean(string='Samedi')
    hor_dim = fields.Boolean(string='Dimanche')

    category_id = fields.Many2one(related='tache_id.category_id', string=u"Type de tâche")
    verif_dispo = fields.Boolean(string=u'Vérif', help=u"Vérifier la disponibilité de l'équipe sur ce créneau", default=True)
#    gb_employee_id = fields.Many2one('hr.employee', compute='lambda *a, **k:{}', search='search_gb_employee_id',
#                                     string="Intervenant", of_custom_groupby=True),
    gb_employee_id = fields.Many2one(related='equipe_id.employee_ids', string="Intervenants", readonly=True, of_custom_groupby=True),

#    _columns = {
#         'color'                : fields_old.function(_get_color, type='char', help=u"Couleur utilisée pour le planning. Dépend de l'équipe d'intervention et de l'état de l'intervention"),
#         'sidebar_color'        : fields_old.related('equipe_id','color_id','color', type='char', help="Couleur pour le menu droit du planning (couleur de base de l'équipe d'intervention)"),
#    }
    _order = 'date'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        name = False
        if self.partner_id:
            name = [self.partner_id.name_get()[0][1]]
            for field in ('zip','city'):
                if self.partner_id.get(field):
                    name.append(self.partner_id[field])
        self.name = name and " ".join(name) or "Intervention"

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        if self.tache_id and self.tache_id.duree:
            self.duree = self.tache_id.duree

    @api.onchange('date', 'duree', 'hor_md', 'hor_mf', 'hor_ad', 'hor_af', 'hor_sam', 'hor_dim')
    def _onchange_date(self):
        if self.hor_md > 24 or self.hor_mf > 24 or self.hor_ad > 24 or self.hor_af > 24:
            raise UserError(u"L'heure doit être inferieure ou égale à 24")
        if self.hor_mf < self.hor_md or self.hor_ad < self.hor_mf:
            raise UserError(u"L'heure de début ne peut pas être supérieure à l'heure de fin")
        if self.hor_ad < self.hor_mf:
            raise UserError(u"L'heure de l'après-midi ne peut pas être inférieure à l'heure du matin")

        if not self.date:
            return
        if not self.duree:
            return

        # Datetime UTC
        dt_utc = datetime.strptime(self.date, "%Y-%m-%d %H:%M:%S")
        # Datetime local
        dt_local = fields.Datetime.context_timestamp(self, dt_utc)

        weekday = dt_local.weekday()
        if weekday == 5 and not self.hor_sam:
            raise UserError(u"L'équipe ne travaille pas le samedi")
        elif weekday == 6 and not self.hor_dim:
            raise UserError(u"L'équipe ne travaille pas le dimanche")

        duree_repos = self.hor_ad - self.hor_mf
        duree_matin = self.hor_mf - self.hor_md
        duree_apres = self.hor_af - self.hor_ad
        duree_jour = duree_matin + duree_apres

        dt_heure = dt_local.hour + (dt_local.minute + dt_local.second / 60) / 60
        # Déplacement de l'horaire de début au début de la journée pour faciliter le calcul
        duree = self.duree
        if self.hor_md <= dt_heure <= self.hor_mf:
            duree += dt_heure - self.hor_md
        elif self.hor_ad <= dt_heure <= self.hor_af:
            duree += duree_matin + dt_heure - self.hor_ad
        else:
            # L'horaire de debut des travaux est en dehors des heures de travail
            raise UserError(u"Il faut respecter l'horaire de travail")
        dt_local -= timedelta(hours=dt_heure)

        if not (self.hor_sam and self.hor_dim):
            # Deplacement de l'horaire de debut au debut de la semaine pour faciliter le calcul
            # Le debut de la semaine peut eventuellement etre un dimanche matin
            jours_sem = (weekday + self.hor_dim) % 6
            dt_local -= timedelta(days=jours_sem)
            duree += jours_sem * duree_jour

            # Ajout des jours de repos a la duree de la tache pour arriver la meme date de fin
            jours = duree // duree_jour
            duree += (self.hor_sam + self.hor_dim) * (jours // (7 - self.hor_sam - self.hor_dim))

        # Calcul du nombre de jours
        jours, duree = duree // duree_jour, duree % duree_jour

        # Ajout des heures non travaillées de la derniere journée
        duree += self.hor_md + (duree > duree_matin and duree_repos)

        # Calcul de la nouvelle date
        dt_local += timedelta(days=jours, hours=duree)
        # Conversion en UTC
        dt_utc = dt_local - dt_local.tzinfo._utcoffset
        date_deadline = dt_utc.strftime("%Y-%m-%d %H:%M:%S")
        self.date_deadline = date_deadline
        self.date_deadline_display = date_deadline

    @api.onchange('equipe_id')
    def _onchange_equipe_id(self):
        equipe = self.equipe_id
        if equipe.hor_md and equipe.hor_mf and equipe.hor_ad and equipe.hor_af:
            self.hor_md = equipe.hor_md
            self.hor_mf = equipe.hor_mf
            self.hor_ad = equipe.hor_ad
            self.hor_af = equipe.hor_af

    @api.multi
    def button_confirm(self):
        return self.write({'state':'confirm'})

    @api.multi
    def button_done(self):
        return self.write({'state':'cone'})

    @api.multi
    def button_postponed(self):
        return self.write({'state':'postponed'})

    @api.multi
    def button_cancel(self):
        return self.write({'state':'cancel'})

    @api.multi
    def button_draft(self):
        return self.write({'state':'draft'})

    @api.multi
    def change_state_after(self):
        next_state = {
            'draft'    : 'confirm',
            'confirm'  : 'done',
            'done'     : 'cancel',
            'cancel'   : 'postponed',
            'postponed': 'draft',
        }
        for intervention in self:
            intervention.state = next_state[intervention.state]
        return True

    @api.multi
    def change_state_before(self):
        previous_state = {
            'draft'    : 'postponed',
            'confirm'  : 'draft',
            'done'     : 'confirm',
            'cancel'   : 'done',
            'postponed': 'cancel',
        }
        for intervention in self:
            intervention.state = previous_state[intervention.state]
        return True

    @api.model
    def create(self, vals):
        # Vérification de la disponibilité du créneau
        if vals.get('verif_dispo') and vals.get('date') and vals.get('date_deadline'):
            rdv = self.search([
                ('equipe_id','=',vals.get('equipe_id')),
                ('date','<',vals['date_deadline']),
                ('date_deadline','>',vals['date']),
                ('state', 'not in', ('cancel','postponed')),
            ])
            if rdv:
                raise ValidationError('Attention', u'Cette équipe a déjà %s rendez-vous sur ce créneau' % (len(rdv),))
        return super(OfPlanningIntervention, self).create(vals)

    @api.multi
    def write(self, vals):
        super(OfPlanningIntervention, self).write(vals)

        # Vérification de la validité du créneau
        for intervention in self:
            if intervention.verif_dispo:
                rdv = self.search([
                    ('equipe_id', '=', intervention.equipe_id.id),
                    ('date', '<', intervention.date_deadline),
                    ('date_deadline', '>', intervention.date),
                    ('id', '!=', intervention.id),
                    ('state', 'not in', ('cancel','postponed')),
                ])
                if rdv:
                    raise ValidationError('Attention', u'Cette équipe a déjà %s rendez-vous sur ce créneau' % (len(rdv),))
        return True

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'gb_employee_id':
            return super(OfPlanningIntervention, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'of_planning_employee_rel', 'equipe_id', 'equipe_id', 'equipe_id'),
            implicit=False, outer=True,
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".employee_id' % (alias,)
        }

class ResPartner(models.Model):
    _inherit = "res.partner"

    intervention_ids = fields.One2many('of.planning.intervention', 'partner_id', "Plannings d'intervention", copy=False)
