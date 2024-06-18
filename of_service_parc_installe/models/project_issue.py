# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    of_a_programmer_count = fields.Integer(compute="_compute_of_a_programmer_count")
    is_migrated = fields.Boolean(string=u"Est migré")

    @api.multi
    def _compute_of_a_programmer_count(self):
        """Smart button vue SAV : renvoi le nombre de demandes d'intervention liées à la machine installée"""
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
        """
        Migre les données des SAV dans les DI.
        Pour les SAV liés à au moins une DI -> remplit les champs de la 1ère DI avec ceux du SAV
        Pour les SAV sans DI -> crée une DI avec toutes les informations du SAV
        """
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            _logger.info(u"OPENFIRE : début de migration des SAV dans les DI (T2356)")
            sav_obj = self.env['project.issue'].with_context(active_test=False)
            service_obj = self.env['of.service'].with_context(active_test=False)
            cr = self.env.cr
            sav_type = self.env.ref('of_service_parc_installe.of_service_type_sav')
            sav_tache = self.env['of.planning.tache'].search([('name', 'ilike', 'SAV')], limit=1)
            if not sav_tache:
                sav_tache = self.env['of.planning.tache'].search([('name', 'ilike', '%SAV%')], limit=1)
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
        || (CASE WHEN pi.stage_id IS NOT NULL
            THEN '
Étape SAV ancienne version: '
            || (SELECT ptt.name FROM project_task_type ptt WHERE ptt.id = pi.stage_id) ELSE '' END)
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
                fields_list = [
                    'create_uid',
                    'create_date',
                    'write_uid',
                    'write_date',
                    'base_state',
                    'titre',
                    'active',
                    'partner_id',
                    'address_id',
                    'company_id',
                    'priority',
                    'user_id',
                    'of_categorie_id',
                    'of_canal_id',
                    'parc_installe_id',
                    'sav_id',
                    'name',
                    'note',
                    'payer_mode',
                    'date_next',
                    'date_fin',
                    'kanban_step_id',
                    'tache_id',
                    'duree',
                    'type_id',
                ]
                query_vals = """
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
        || (CASE WHEN pi.stage_id IS NOT NULL
            THEN '
Étape SAV ancienne version: '
            || (SELECT ptt.name FROM project_task_type ptt WHERE ptt.id = pi.stage_id) ELSE '' END)
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
    (SELECT opimwsl.service_step_id
    FROM of_project_issue_migration_wizard_step_line opimwsl
    WHERE opimwsl.sav_step_id = pi.stage_id) AS kanban_step_id,
    %s,
    %s,
    %s
"""
                query_params = [sav_tache.id, sav_tache.id, sav_tache.duree, sav_type.id]

                # Ajout des valeurs par défaut
                fields_list_default = [
                    field_name
                    for field_name, field in service_obj._fields.iteritems()
                    if field.store
                    if field_name not in fields_list
                    if field.type not in ('one2many', 'many2many')
                    if not field.company_dependent
                ]
                for field_name, value in service_obj.default_get(fields_list_default).iteritems():
                    if not value:
                        continue
                    fields_list.append(field_name)
                    query_vals += ",\n    %s"
                    query_params.append(value)

                query_fields = ",\n    ".join(fields_list)
                cr.execute("""INSERT INTO of_service (
    """ + query_fields + """
)
(
SELECT""" + query_vals + """
FROM project_issue pi
WHERE pi.id in %s
)""", query_params + [sav_sans_di._ids])

            # noter tous les SAV avec partenaire comme "migrés"
            (sav_avec_di | sav_sans_di).write({'is_migrated': True})

            _logger.info(u"OPENFIRE : rattacher aux DI les étiquettes en provenance des SAV")

            # Créer les étiquettes de planning, à partir des étiquettes de SAV. Attention aux doublons!
            # Ne pas créer si il y a une étiquette planning du même nom
            cr.execute("INSERT INTO of_planning_tag "
                       "(name, color, create_uid, write_uid, create_date, write_date, active) "
                       "SELECT pt.name, pt.color, pt.create_uid, pt.write_uid, pt.create_date, pt.write_date, true "
                       "FROM project_tags AS pt "
                       "WHERE UPPER(pt.name) NOT IN (SELECT UPPER(name) FROM of_planning_tag);")
            # connecter les étiquettes aux DI
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

            self.env['ir.config_parameter'].sudo().set_param('of_migration_sav_di', True)
            # retirer le groupe project_issue_not_migrated pour masquer les menus de SAV
            group_not_migrated = self.env.ref('of_service_parc_installe.group_of_project_issue_not_migrated')
            group_user = self.env.ref('base.group_user')
            if group_not_migrated in group_user.implied_ids:
                group_user.write({'implied_ids': [(3, group_not_migrated.id)]})
            # des utilisateurs sont encore dans le groupe SAV non migrés, on le leur retire
            if group_not_migrated.users:
                group_not_migrated.users.write({'groups_id': [(3, group_not_migrated.id)]})
            _logger.info(u"OPENFIRE SUCCÈS : migration des SAV dans les DI (T2356)")


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
