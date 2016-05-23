# -*- encoding: utf-8 -*-

from openerp import api, models, fields


class of_mois(models.Model):
    _name = 'of.mois'
    _description = u"Mois de l'année"
    _order = 'id'

    name = fields.Char('Mois', size=16)
    abr = fields.Char(u'Abréviation', size=16)


class of_jours(models.Model):
    _name = 'of.jours'
    _description = "Jours de la semaine"
    _order = 'id'

    name = fields.Char('Jour', size=16)
    abr = fields.Char(u'Abréviation', size=16)


class of_service(models.Model):
    _name = "of.service"
    _description = "Service"

    @api.one
    @api.depends('mois_ids')
    def _get_mois_str(self):
        self.mois_str = " ".join([mois.abr for mois in self.mois_ids])

    @api.one
    @api.depends('jour_ids')
    def _get_jour_dis(self):
        self.jours_str = " ".join([jour.abr for jour in self.jour_ids])

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        # Pour que les jours apparaissent dans le bon ordre, il faut les envoyer dans l'ordre inverse
        return [5, 4, 3, 2, 1]

    def _search_mois(self, operator, value):
        mois = self.env['of.mois'].search(['|', ('name', operator, value), ('abr', operator, value)])
        return [('mois_ids', 'in', mois.ids)]

    def _search_jour(self, operator, value):
        jours = self.env['of.jours'].search(['|', ('name', operator, value), ('abr', operator, value)])
        return [('jour_ids', 'in', jours.ids)]

    template_id = fields.Many2one('of.mail.template', string='Contrat')
    partner_id = fields.Many2one('res.partner', string='Partenaire', store=True, ondelete='cascade')

    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    name = fields.Char(u"Libellé", related='tache_id.name', store=True)

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois', required=True)
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours', required=True, default=_get_default_jours)

    mois_ids_str = fields.Char("Mois", compute='get_mois_str', search='_search_mois')
    jour_ids_str = fields.Char("Jours", compute='get_jours_str', search='_search_jour')

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


class res_partner(models.Model):
    _inherit = "res.partner"

    service_ids = fields.One2many('of.service', 'partner_id', string='Service')

