# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import date
from datetime import timedelta

class OfService(models.Model):
    _name = "of.service"
    _inherit = "of.map.view.mixin"
    _description = "Service"

    @api.model_cr_context
    def _auto_init(self):
        # A SUPRIMER
        # Mise à jour du champ company_id des services existants
        cr = self._cr
        fill_company_id = False
        if self._auto:
            cr.execute("SELECT * FROM information_schema.columns WHERE table_name = 'of_service' AND column_name = 'company_id'")
            fill_company_id = not bool(cr.fetchall())

        res = super(OfService, self)._auto_init()
        if fill_company_id:
            cr.execute("UPDATE of_service AS s "
                       "SET company_id = p.company_id\n"
                       "FROM res_partner AS p\n"
                       "WHERE p.id = s.partner_id")
        return res

    def _default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    @api.one
    @api.depends('tache_id', 'address_id')
    def _compute_planning_ids(self):
        planning_obj = self.env['of.planning.intervention']
        for service in self:
            plannings = planning_obj.search([('tache_id', '=', service.tache_id.id),
                                             ('address_id', '=', service.address_id.id)], order='date desc')
            service.planning_ids = plannings
            service.date_last = plannings and plannings[0].date or False

    @api.model
    def _search_last_date(self, operator, operand):
        cr = self._cr

        query = ("SELECT s.id\n"
                 "FROM of_service AS s\n"
                 "LEFT JOIN of_planning_intervention AS p\n"
                 "  ON p.address_id = s.address_id\n"
                 "  AND p.tache_id = s.tache_id\n")

        if operand:
            if len(operand) == 10:
                # Copié depuis osv/expression.py
                if operator in ('>', '<='):
                    operand += ' 23:59:59'
                else:
                    operand += ' 00:00:00'
            query += ("GROUP BY s.id\n"
                      "HAVING MAX(p.date) %s '%s'" % (operator, operand))
        else:
            if operator == '=':
                query += "WHERE p.id IS NULL"
            else:
                query += "WHERE p.id IS NOT NULL"
        cr.execute(query)
        rows = cr.fetchall()
        return [('id', 'in', rows and zip(*rows)[0])]

    @api.multi
    @api.depends('date_next')
    def _compute_color(self):
        u""" COULEURS :
        Gris  : service dont l'adresse n'a pas de coordonnées GPS, ou service inactif
        Orange: service dont la date de prochaine intervention est dans moins d'un mois
        Rouge : service dont la date de prochaine intervention est inférieure à la date courante (ou à self._context.get('date_next_max'))
        Noir  : autres services
        """
        date_next_max = fields.Date.from_string(self._context.get('date_next_max') or fields.Date.today())

        for service in self:
            date_next = fields.Date.from_string(service.date_next)
            if not (service.address_id.geo_lat or service.address_id.geo_lng) or not service.active:
                service.color = 'gray'
            elif date_next <= date_next_max:
                service.color = 'red'
            elif date_next <= date_next_max + timedelta(days=30):
                service.color = 'orange'
            else:
                service.color = 'black'

    @api.model
    def get_color_map(self):
        u"""
        fonction pour la légende de la vue map
        """
        title = "Prochaine Intervention"
        v0 = {'label': "Plus d'un mois", 'value': 'black'}
        v1 = {'label': u'Ce mois-ci', 'value': 'orange'}
        v2 = {'label': u'En retard', 'value': 'red'}
        return {"title": title, "values": (v0, v1, v2)}

    # template_id = fields.Many2one('of.mail.template', string='Contrat')
    partner_id = fields.Many2one('res.partner', string='Partenaire', ondelete='restrict')
    address_id = fields.Many2one('res.partner', string="Adresse", ondelete='restrict')
    company_id = fields.Many2one('res.company', string=u"Société")

    # Champs ajoutés pour la vue map
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')
    precision = fields.Selection(related='address_id.precision')
    partner_name = fields.Char(related='partner_id.name')
    partner_mobile = fields.Char(related='partner_id.mobile')

    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    name = fields.Char(u"Libellé", related='tache_id.name', store=True)
    tag_ids = fields.Many2many('of.service.tag', string=u"Étiquettes")

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois', required=True)
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours', required=True, default=_default_jours)

    note = fields.Text('Notes')
    date_next = fields.Date('Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention", required=True)
    date_fin = fields.Date(u"Date d'échéance")

    # Partner-related fields
    partner_zip = fields.Char('Code Postal', size=24, related='address_id.zip')
    partner_city = fields.Char('Ville', related='address_id.city')

    state = fields.Selection([
        ('progress', 'En cours'),
        ('cancel', u'Annulé'),
        ], u'État')
    active = fields.Boolean(string="Active", default=True)

    planning_ids = fields.One2many('of.planning.intervention', compute='_compute_planning_ids', string="Interventions")
    date_last = fields.Date(
        string=u'Dernière intervention', compute='_compute_planning_ids', search='_search_last_date',
        help=u"Date de la dernière intervention")

    # Champs de recherche
    date_fin_min = fields.Date(string=u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date(string=u"Date échéance max", compute='lambda *a, **k:{}')
    date_controle = fields.Date(string=u"Date de contrôle", compute='lambda *a, **k:{}')

    # Couleur de contrôle
    color = fields.Char(compute='_compute_color', string='Couleur', store=False)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.company_id = self.partner_id.company_id

    @api.onchange('date_next')
    def _onchange_date_next(self):
        # Remplissage automatique du mois en fonction de la date de prochaine intervention choisie
        # /!\ Un simple clic sur le champ date appelle cette fonction, et génère le mois avec la date courante
        #       avant que l'utilisateur ait confirmé son choix.
        #     Cette fonction doit donc être autorisée à écraser le mois déjà saisi
        #     Pour éviter les ennuis, elle est donc restreinte à un usage en mode création de nouveau service uniquement
        if self.date_next and not self._origin:  # <- signifie mode creation
            mois = self.env['of.mois'].search([('numero', '=', int(self.date_next[5:7]))])
            mois_id = mois[0] and mois[0].id or False
            if mois_id:
                self.mois_ids = [(4, mois_id, 0)]

    @api.multi
    def get_next_date(self, date_str):
        self.ensure_one()
        mois_nums = self.mois_ids.mapped('numero')

        date_date = fields.Date.from_string(max(date_str, self.date_last))
        date_mois = date_date.month
        date_annee = date_date.year

        if (date_mois not in mois_nums) and (date_mois+1 in mois_nums):
            # Le rdv a été pris en avance pour le mois suivant
            date_mois += 1

        mois = min(mois_nums, key=lambda m: (m <= date_mois, m))
        annee = date_annee + (mois <= date_mois)
        return fields.Date.to_string(date(annee, mois, 1))

    @api.model
    def create(self, vals):
        if vals.get('address_id') and not vals.get('partner_id'):
            address = self.env['res.partner'].browse(vals['address_id'])
            partner = address.parent_id or address
            vals['partner_id'] = partner.id
        return super(OfService, self).create(vals)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(OfService, self).search(args, offset, limit, order, count)
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(OfService, self).read(fields, load)
        return res

class OFServicesTag(models.Model):
    _name = 'of.service.tag'
    _description = u"Étiquettes des services"

    name = fields.Char(string=u"Libellé", required=True)
    active = fields.Boolean(string='Actif', default=True)

class OFPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    service_id = fields.Many2one('of.service', string="Service")

    @api.onchange('address_id')
    def _onchange_address_id(self):
        super(OFPlanningIntervention, self)._onchange_address_id()
        if self.address_id and self.address_id.service_address_ids:
            self.service_id = self.address_id.service_address_ids[0]

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.tache_id = self.service_id.tache_id

class ResPartner(models.Model):
    _inherit = "res.partner"

    service_address_ids = fields.One2many('of.service', 'address_id', string='Services', context={'active_test': False})
    service_partner_ids = fields.One2many('of.service', 'partner_id', string='Services du partenaire', context={'active_test': False},
                                          help="Services liés au partenaire, incluant les services des contacts associés")
