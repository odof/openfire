# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class OfService(models.Model):
    _inherit = "of.service"

    parc_installe_id = fields.Many2one(comodel_name='of.parc.installe', string=u"No de série")
    parc_installe_product_id = fields.Many2one(
        'product.product', string=u"Désignation", related="parc_installe_id.product_id", readonly=True)
    parc_installe_site_adresse_id = fields.Many2one(
        'res.partner', string=u"Adresse de pose", related="parc_installe_id.site_adresse_id", readonly=True)
    parc_installe_note = fields.Text(string=u"Note", related="parc_installe_id.note", readonly=True)
    sav_id = fields.Many2one(
        "project.issue", string="SAV", domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")
    parc_type_garantie = fields.Selection(related='parc_installe_id.type_garantie')

    of_categorie_id = fields.Many2one('of.project.issue.categorie', string=u"Catégorie", ondelete='restrict')
    of_canal_id = fields.Many2one('of.project.issue.canal', string=u"Canal", ondelete='restrict')

    @api.depends('parc_installe_id.intervention_ids', 'address_id.intervention_address_ids',
                 'partner_id.intervention_address_ids')
    def _compute_historique_interv_ids(self):
        for service in self:
            if service.parc_installe_id:
                service.historique_interv_ids = service.parc_installe_id.intervention_ids
            else:
                super(OfService, self)._compute_historique_interv_ids()

    @api.onchange('address_id')
    def _onchange_address_id(self):
        self.ensure_one()
        if self.address_id and (not self.parc_installe_id or self.parc_installe_site_adresse_id != self.address_id):
            parc_obj = self.env['of.parc.installe']
            if not parc_obj.check_access_rights('read', raise_exception=False):
                # ne pas tenter le onchange si n'a pas les droits
                return
            parc_installe = parc_obj.search([('site_adresse_id', '=', self.address_id.id)], limit=1)
            if not parc_installe:
                parc_installe = parc_obj.search([('client_id', '=', self.address_id.id)], limit=1)
            if not parc_installe and self.partner_id:
                parc_installe = parc_obj.search([('client_id', '=', self.partner_id.id)], limit=1)
            if parc_installe:
                self.parc_installe_id = parc_installe

    @api.onchange('sav_id')
    def _onchange_sav_id(self):
        self.ensure_one()
        if self.sav_id:
            self.date_fin = self.get_fin_date()

    @api.multi
    def get_fin_date(self, date_str=False):
        """
        :param date_str: Date de prochaine planif à utiliser pour le calcul, sous format string
        :return: Date à partir de laquelle l'intervention passe à l'état 'en retard'
        :rtype string
        """
        self.ensure_one()
        date_next_str = date_str or self.date_next or False

        if date_next_str:
            date_fin = fields.Date.from_string(date_next_str)
            if (not self.tache_id or not self.tache_id.fourchette_planif) and self.sav_id:
                # une semaine par défaut pour les SAV
                date_fin += relativedelta(weeks=1)
                date_fin -= relativedelta(days=1)
                # ^- moins 1 jour car les intervalles de dates sont inclusifs
                return fields.Date.to_string(date_fin)
            else:
                return super(OfService, self).get_fin_date(date_next_str)
        else:
            return ""

    @api.multi
    def get_action_view_intervention_context(self, context={}):
        context = super(OfService, self).get_action_view_intervention_context(context)
        context['default_parc_installe_id'] = self.parc_installe_id and self.parc_installe_id.id or False
        context['default_sav_id'] = self.sav_id and self.sav_id.id or False
        return context


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    parc_installe_id = fields.Many2one(
        'of.parc.installe', string=u"Parc installé",
        domain="['|', '|', ('client_id', '=', partner_id), ('client_id', '=', address_id), "
               "('site_adresse_id', '=', address_id)]")
    parc_installe_product_name = fields.Char(
        string=u"Désignation", related="parc_installe_id.product_id.name", readonly=True)

    @api.model
    def create(self, vals):
        service_obj = self.env['of.service']
        parc_obj = self.env['of.parc.installe']
        service = vals.get('service_id') and service_obj.browse(vals['service_id'])
        parc = False
        if service:
            parc = service.parc_installe_id
            vals['parc_installe_id'] = parc and parc.id
        parc = not parc and vals.get('parc_installe_id') and parc_obj.browse(vals['parc_installe_id'])
        return super(OfPlanningIntervention, self).create(vals)

    @api.multi
    def button_open_of_planning_intervention(self):
        if self.ensure_one():
            return {
                'name': 'of.planning.intervention.form',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.planning.intervention',
                'res_id': self._ids[0],
                'type': 'ir.actions.act_window',
            }


class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    intervention_ids = fields.One2many('of.planning.intervention', 'parc_installe_id', string="Interventions")
    service_count = fields.Integer(compute="_compute_service_count")
    a_programmer_count = fields.Integer(compute="_compute_service_count")

    @api.multi
    def _compute_service_count(self):
        """Smart button vue parc installé : renvoi le nombre de service lié à la machine installée"""
        service_obj = self.env['of.service']
        for parc in self:
            services = service_obj.search([('parc_installe_id', '=', parc.id)])  # permet de ne faire d'un seul search
            parc.service_count = len(services.filtered('recurrence'))
            parc.a_programmer_count = len(services.filtered(lambda s: not s.recurrence))

    @api.multi
    def action_view_service(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_service').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id), ('recurrence', '=', True)]
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': True,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_service.of_service_type_maintenance').id,
        }
        return action

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id), ('recurrence', '=', False)]
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_service.of_service_type_maintenance').id,
        }
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[Parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_service.of_service_type_maintenance').id,
        }
        return action

    @api.multi
    def historique(self, intervention):
        """
        :param intervention: Intervention de départ
        :return: Renvoi les 3 interventions précédent celle envoyée en paramètre.
        """
        self.ensure_one()
        return self.env['of.planning.intervention'].search([
            ('id', 'in', self.intervention_ids.ids),
            ('date', '<', intervention.date)
            ], order="date DESC", limit=3)


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    of_a_programmer_count = fields.Integer(compute="_compute_of_a_programmer_count")
    is_migrated = fields.Boolean(string=u"Est migré")

    @api.multi
    def _compute_of_a_programmer_count(self):
        """Smart button vue SAV : renvoi le nombre d'interventions à programmer liées à la machine installée"""
        service_obj = self.env['of.service']
        for sav in self:
            sav.of_a_programmer_count = len(service_obj.search([('sav_id', '=', sav.id), ('recurrence', '=', False)]))

    @api.multi
    def action_view_a_programmer(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['domain'] = [('sav_id', '=', self.id), ('recurrence', '=', False)]
        action['context'] = {
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
            'default_type_id': self.env.ref('of_service_parc_installe.of_service_type_sav').id,
        }
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
            'default_type_id': self.env.ref('of_service_parc_installe.of_service_type_sav').id,
        }
        return action

    @api.model
    def migrer_sav_di(self):
        u"""
        Migre les données des SAV dans les DI.
        Pour les SAV liés à au moins une DI -> rempli les champ de la 1ère DI avec ceux du SAV
        Pour les SAV sans DI -> créé une DI avec toutes les informations du SAV
        """
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            _logger.info(u"OPENFIRE : début de migration des SAV dans les DI (T2356)")
            sav_obj = self.env['project.issue']
            service_obj = self.env['of.service']
            cr = self.env.cr
            sav_type = self.env.ref('of_service_parc_installe.of_service_type_sav')
            sav_tache  = self.env['of.planning.tache'].search([('name', 'ilike', 'SAV')], limit=1)
            if not sav_tache:
                sav_tache  = self.env['of.planning.tache'].search([('name', 'ilike', '%SAV%')], limit=1)
                if not sav_tache:
                    _logger.error(u"OPENFIRE ERROR : impossible de migrer les SAV dans les DI, tâche 'SAV' inexistante")
                    return

            # Ne pas toucher aux SAV déjà migrés
            # Mettre à jour les DI des SAV avec DI, créer des DI pour les autres
            sav_avec_di = service_obj.search([('sav_id', '!=', False)]).mapped('sav_id')\
                .filtered(lambda s: not s.is_migrated)
            # ne pas essayer de migrer les SAV sans partenaire
            sav_sans_di = sav_obj.search([('is_migrated', '=', False), ('partner_id', '!=', False)]) - sav_avec_di

            if sav_avec_di:
                _logger.info(u"OPENFIRE : mise à jour des DI liées à un SAV")
                cr.execute("""UPDATE of_service os SET
    titre = COALESCE ( os.titre, pi.name ),
    active = COALESCE ( os.active, pi.active ),
    partner_id = COALESCE ( os.partner_id, pi.partner_id ),
    address_id = COALESCE ( os.address_id, pi.partner_id ),
    company_id = COALESCE ( os.company_id, pi.company_id ),
    priority = COALESCE ( os.priority, pi.priority ),
    user_id = COALESCE ( os.user_id, pi.user_id ),
    of_categorie_id = COALESCE ( os.of_categorie_id, pi.of_categorie_id ),
    of_canal_id = COALESCE ( os.of_canal_id, pi.of_canal_id ),
    parc_installe_id = COALESCE ( os.parc_installe_id, pi.of_produit_installe_id ),
    note = COALESCE ( os.note, pi.description
        || (CASE WHEN pi.of_intervention IS NOT NULL 
            THEN '
Nature de l''intervention: ' || pi.of_intervention ELSE '' END)
        || (CASE WHEN pi.of_piece_commande IS NOT NULL
            THEN '
Pièces à commander: ' || pi.of_piece_commande ELSE '' END)
        || '
nº SAV ancienne version: ' || pi.of_code
        || (CASE WHEN pi.product_name_id IS NOT NULL AND pi.of_produit_installe_id IS NULL 
            THEN '
Article associé ancienne version: ['
                || (SELECT pp1.default_code FROM product_product pp1 WHERE pp1.id = pi.product_name_id) 
                || '] '
                || (SELECT pt.name
                    FROM product_product pp2 JOIN product_template pt ON pt.id = pp2.product_tmpl_id
                    WHERE pp2.id = pi.product_name_id) ELSE '' END )),
    payer_mode = COALESCE ( os.payer_mode,
                            CASE
                                WHEN pi.of_payant_client AND pi.of_payant_fournisseur THEN 'retailer'
                                WHEN pi.of_payant_client THEN 'client'
                                WHEN pi.of_payant_fournisseur THEN 'manufacturer'
                                ELSE NULL
                            END),
    type_id = %s
FROM project_issue pi
WHERE os.sav_id = pi.id AND pi.id in %s""", (sav_type.id, sav_avec_di._ids))

            if sav_sans_di:
                _logger.info(u"OPENFIRE : création de DI pour les SAV sans DI")
                cr.execute("""INSERT INTO of_service (
    create_uid,
    create_date,
    write_uid,
    write_date,
    base_state,
    titre,
    active,
    partner_id,
    address_id,
    company_id,
    priority,
    user_id,
    of_categorie_id,
    of_canal_id,
    parc_installe_id,
    sav_id,
    name,
    note,
    payer_mode,
    date_next,
    date_fin,
    tache_id,
    duree,
    type_id
)
(
SELECT
    1,
    now(),
    1,
    now(),
    'calculated',
    pi.name,
    pi.active,
    pi.partner_id,
    pi.partner_id,
    pi.company_id,
    pi.priority,
    pi.user_id,
    pi.of_categorie_id,
    pi.of_canal_id,
    pi.of_produit_installe_id,
    pi.id,
    (SELECT rp.name || ' ' || rp.zip FROM res_partner rp WHERE rp.id = pi.partner_id)
        || ' ' || (SELECT opt.name FROM of_planning_tache opt WHERE opt.id = %s),
    pi.description
        || (CASE WHEN pi.of_intervention IS NOT NULL
            THEN '
Nature de l''intervention: ' || pi.of_intervention ELSE '' END)
        || (CASE WHEN pi.of_piece_commande IS NOT NULL
            THEN '
Pièces à commander: ' || pi.of_piece_commande ELSE '' END)
        || '
nº SAV ancienne version: ' || pi.of_code
        || (CASE WHEN pi.product_name_id IS NOT NULL AND pi.of_produit_installe_id IS NULL
            THEN '
Article associé ancienne version: [' 
                || (SELECT pp1.default_code FROM product_product pp1 WHERE pp1.id = pi.product_name_id)
                || '] '
                || (SELECT pt.name
                    FROM product_product pp2
                    JOIN product_template pt ON pt.id = pp2.product_tmpl_id
                    WHERE pp2.id = pi.product_name_id) ELSE '' END),
    CASE
        WHEN pi.of_payant_client AND pi.of_payant_fournisseur THEN 'retailer'
        WHEN pi.of_payant_client THEN 'client'
        WHEN pi.of_payant_fournisseur THEN 'manufacturer'
        ELSE NULL
    END AS payer_mode,
    CASE WHEN pi.date IS NOT NULL THEN pi.date::date ELSE CURRENT_DATE END AS date_next,
    CASE
        WHEN pi.date IS NULL AND pi.date_deadline IS NULL THEN CURRENT_DATE + integer '7'
        WHEN pi.date_deadline IS NULL OR pi.date_deadline < pi.date THEN pi.date::date + integer '7'
        ELSE pi.date_deadline::date
    END AS date_fin,
    %s,
    %s,
    %s
FROM project_issue pi
WHERE pi.id in %s
)""", (sav_tache.id, sav_tache.id, sav_tache.duree, sav_type.id, sav_sans_di._ids))

            # noter tous les SAV avec partenaire comme "migrés"
            (sav_avec_di | sav_sans_di).write({'is_migrated': True})

            _logger.info(u"OPENFIRE : rattacher aux DI les étiquettes en provenance des SAV")
            cr.execute("""INSERT INTO of_service_of_planning_tag_rel (service_id, tag_id)
SELECT os.id, opt.id
FROM of_service os
JOIN project_issue_project_tags_rel pipt ON pipt.project_issue_id = os.sav_id
JOIN project_tags pt ON pt.id = pipt.project_tags_id
JOIN of_planning_tag opt ON UPPER(opt.name) = UPPER(pt.name)
ON CONFLICT DO NOTHING""")

            _logger.info(u"OPENFIRE : rattacher aux DI les RDV liés à des SAV")
            cr.execute("""UPDATE of_planning_intervention opi
SET service_id = os.id
FROM project_issue pi
JOIN of_service os ON os.sav_id = pi.id
WHERE opi.sav_id = pi.id""")

            _logger.info(u"OPENFIRE : calculer les champs difficiles à traduire en SQL pour les DI nouvellement créées")
            # calculer l'état des DI nouvellement créées. Leur affecter un numéro. En python car compliqué en SQL
            service_new = service_obj.search([('sav_id', 'in', sav_sans_di.ids)])
            service_new._compute_state_poncrec()
            service_obj._init_number()

            _logger.info(u"OPENFIRE SUCCÈS : migration des SAV dans les DI (T2356)")
            self.env['ir.config_parameter'].sudo().set_param('of_migration_sav_di', True)


class ProjectTags(models.Model):
    _inherit = 'project.tags'

    @api.model_cr_context
    def _auto_init(self):
        u"""
        Fusion de project.tags dans of.planning.tag
        """
        cr = self._cr
        res = super(ProjectTags, self)._auto_init()
        # ce param de config est passé à True dans la fonction "migrer_sav_di"
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            # Créer les étiquettes de planning. Attention aux doublons!
            # Ne pas créer si il y a une étiquette planning du même nom
            # on ne rattache pas ici les étiquettes nouvellement crées, on le fera dans la méthode migrer_sav_di
            cr.execute("INSERT INTO of_planning_tag "
                       "(name, color, create_uid, write_uid, create_date, write_date, active) "
                       "SELECT pt.name, pt.color, pt.create_uid, pt.write_uid, pt.create_date, pt.write_date, true "
                       "FROM project_tags AS pt "
                       "WHERE UPPER(pt.name) NOT IN (SELECT UPPER(name) FROM of_planning_tag);")
        return res
