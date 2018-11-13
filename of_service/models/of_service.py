# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import date
from datetime import timedelta

class OfService(models.Model):
    _name = "of.service"
    _inherit = "of.map.view.mixin"
    _description = "Service"

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    def _search_mois(self, operator, value):
        mois = self.env['of.mois'].search(['|', ('name', operator, value), ('abr', operator, value)])
        return [('mois_ids', 'in', mois.ids)]

    def _search_jour(self, operator, value):
        jours = self.env['of.jours'].search(['|', ('name', operator, value), ('abr', operator, value)])
        return [('jour_ids', 'in', jours.ids)]

    @api.one
    @api.depends('tache_id', 'address_id')
    def _get_planning_ids(self):
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

    # Champs ajoutés pour la vue map
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')
    precision = fields.Selection(related='address_id.precision')
    partner_name = fields.Char(related='partner_id.name')
    partner_mobile = fields.Char(related='partner_id.mobile')

    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    name = fields.Char(u"Libellé", related='tache_id.name', store=True)

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois', required=True)
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours', required=True, default=_get_default_jours)

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

    planning_ids = fields.One2many('of.planning.intervention', compute='_get_planning_ids', string="Interventions")
    date_last = fields.Date(u'Dernière intervention', compute='_get_planning_ids', search='_search_last_date', help=u"Date de la dernière intervention")

    # Champs de recherche
    date_fin_min = fields.Date(string=u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date(string=u"Date échéance max", compute='lambda *a, **k:{}')
    date_controle = fields.Date(string=u"Date de contrôle", compute='lambda *a, **k:{}')

    # Couleur de contrôle
    color = fields.Char(compute='_compute_color', string='Couleur', store=False)

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

class ResPartner(models.Model):
    _inherit = "res.partner"

    service_address_ids = fields.One2many('of.service', 'address_id', string='Services', context={'active_test': False})
    service_partner_ids = fields.One2many('of.service', 'partner_id', string='Services du partenaire', context={'active_test': False},
                                          help="Services liés au partenaire, incluant les services des contacts associés")
