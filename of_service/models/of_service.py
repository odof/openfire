# -*- encoding: utf-8 -*-

from odoo import api, models, fields


class OfMois(models.Model):
    _name = 'of.mois'
    _description = u"Mois de l'année"
    _order = 'id'

    name = fields.Char('Mois', size=16)
    abr = fields.Char(u'Abréviation', size=16)


class OfJours(models.Model):
    _name = 'of.jours'
    _description = "Jours de la semaine"
    _order = 'id'

    name = fields.Char('Jour', size=16)
    abr = fields.Char(u'Abréviation', size=16)


class OfService(models.Model):
    _name = "of.service"
    _description = "Service"

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        return [1, 2, 3, 4, 5]

    def _search_mois(self, operator, value):
        mois = self.env['of.mois'].search(['|', ('name', operator, value), ('abr', operator, value)])
        return [('mois_ids', 'in', mois.ids)]

    def _search_jour(self, operator, value):
        jours = self.env['of.jours'].search(['|', ('name', operator, value), ('abr', operator, value)])
        return [('jour_ids', 'in', jours.ids)]

    @api.one
    @api.depends('tache_id','partner_id')
    def _get_planning_ids(self):
        planning_obj = self.env['of.planning.intervention']
        for service in self:
            plannings = planning_obj.search([('tache_id','=',service.tache_id.id),
                                             ('partner_id','=',service.partner_id.id)], order='date desc')
            service.planning_ids = plannings
            service.date_last = plannings and plannings[0].date or False

    @api.model
    def _search_last_date(self, operator, operand):
        cr = self._cr
        print [('date_last', operator, operand)]

        query = ("SELECT s.id\n"
                 "FROM of_service AS s\n"
                 "LEFT JOIN of_planning_intervention AS p\n"
                 "  ON p.partner_id = s.partner_id\n"
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
        return [('id', 'in', zip(*rows)[0])]

#    template_id = fields.Many2one('of.mail.template', string='Contrat')
    partner_id = fields.Many2one('res.partner', string='Partenaire', store=True, ondelete='cascade')
    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    name = fields.Char(u"Libellé", related='tache_id.name', store=True)

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois', required=True)
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours', required=True, default=_get_default_jours)

    note = fields.Text('Notes')
    date_fin = fields.Date(u"Date d'échéance")
    date_fin_min = fields.Date(u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date("max", compute='lambda *a, **k:{}')

    # Partner-related fields
    partner_zip = fields.Char('Code Postal', size=24, related='partner_id.zip')
    partner_city = fields.Char('Ville', related='partner_id.city')

    state = fields.Selection([
            ('progress', 'En cours'),
            ('cancel', u'Annulé'),
            ], 'Etat', default='progress')

    planning_ids = fields.One2many('of.planning.intervention', compute='_get_planning_ids', string="Interventions")
    date_last = fields.Date(u'Dernière intervention', compute='_get_planning_ids', search='_search_last_date', help=u"Date de la dernière intervention")

class ResPartner(models.Model):
    _inherit = "res.partner"

    service_ids = fields.One2many('of.service', 'partner_id', string='Service')

