# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
import os
import base64
import tempfile
try:
    import pypdftk
except ImportError:
    pypdftk = None


class OfPlanningInterventionTemplate(models.Model):
    _name = 'of.planning.intervention.template'

    @api.model_cr_context
    def _auto_init(self):
        old_default_template = self.env['ir.model.data'].search([
            ('name', '=', 'of_planning_default_intervention_template'),
            ('module', '=', 'of_mobile')
            ])
        res = super(OfPlanningInterventionTemplate, self)._auto_init()
        if old_default_template:
            default = self.env.ref('of_mobile.of_planning_default_intervention_template', raise_if_not_found=False)
            old_default_template.write({'module': 'of_planning'})
            default.write({
                'fi_default': False,
                'fi_title': "Fiche d'intervention",
                'fi_order': True,
                'fi_order_client': True,
                'fi_order_name': True,
                'fi_order_interv_label': True,
                'fi_products': True,
                'fi_products_order': True,
                'fi_rdv': True,
                'fi_rdv_date_start': True,
                'fi_rdv_date_end': True,
                'fi_rdv_task': True,
                'fi_rdv_task_description': True,
                'fi_rdv_duration': True,
                'fi_rdv_tech': True,
                'fi_rdv_address': True,
                'fi_rdv_mail': True,
                'fi_rdv_phone': True,
                'fi_description': True,
                'fi_description_ext': True,
                'fi_invoicing': True,
                'fi_invoicing_ht': True,
                'fi_invoicing_taxes': True,
                'fi_invoicing_ttc': True,
            })
            # self.env.cr.execute(
            #     "UPDATE of_planning_intervention_template "
            #     "SET fi_title = 'Fiche d'intervention', "
            #     "fi_order = 't', "
            #     "fi_order_client = 't', "
            #     "fi_order_name = 't', "
            #     "fi_order_interv_label = 't', "
            #     "fi_products = 't', "
            #     "fi_products_order = 't', "
            #     "fi_rdv = 't', "
            #     "fi_rdv_date_start = 't', "
            #     "fi_rdv_date_end = 't', "
            #     "fi_rdv_task = 't', "
            #     "fi_rdv_task_description = 't', "
            #     "fi_rdv_duration = 't', "
            #     "fi_rdv_tech = 't', "
            #     "fi_rdv_address = 't', "
            #     "fi_rdv_mail = 't', "
            #     "fi_rdv_phone = 't', "
            #     "fi_description = 't', "
            #     "fi_rdv_mail = 't', "
            #     "fi_description_ext = 't', "
            #     "fi_invoicing = 't', "
            #     "fi_invoicing_ht = 't', "
            #     "fi_invoicing_taxes = 't', "
            #     "fi_invoicing_ttc = 't' "
            #     "WHERE id = %s", (default.id,))
        return res

    @api.model
    def _get_default_template_values(self):
        res = self._get_default_template_values_fi()
        res.update(self._get_default_template_values_ri())
        return res

    @api.model
    def _get_default_template_values_fi(self):
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        values = {}
        if default_template:
            copy = default_template.copy_data()[0] or {}
            for key, value in copy.iteritems():
                # copier les valeurs du rapport d'intervention
                if isinstance(key, basestring) and key.startswith("fi_") and key != 'fi_default':
                    values[key] = value
        return values

    @api.model
    def _get_default_template_values_ri(self):
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        values = {}
        if default_template:
            copy = default_template.copy_data()[0] or {}
            for key, value in copy.iteritems():
                # copier les valeurs du rapport d'intervention
                if isinstance(key, basestring) and key.startswith("ri_") and key != 'ri_default':
                    values[key] = value
        return values

    @api.model
    def default_get(self, fields_list):
        res = super(OfPlanningInterventionTemplate, self).default_get(fields_list)
        default_template_values = self._get_default_template_values()
        if default_template_values:
            if isinstance(res, dict):
                res.update(default_template_values)
            else:
                res = default_template_values
        return res

    name = fields.Char(string=u"Nom du modèle", required=True)
    active = fields.Boolean(string="Active", default=True)
    code = fields.Char(string="Code", compute="_compute_code", inverse="_inverse_code", store=True, required=True)
    sequence_id = fields.Many2one('ir.sequence', string=u"Séquence", readonly=True)
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche")
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale", company_dependent=True)
    line_ids = fields.One2many('of.planning.intervention.template.line', 'template_id', string="Lignes de facturation")

    is_default_template = fields.Boolean(compute="_compute_is_default_template")
    # FICHE D'INTERVENTION
    fi_default = fields.Boolean(string=u"Rapport par défaut", default=True)
    fi_title = fields.Char(string="Titre du rapport", default="Rapport d'intervention")
    # -- FI - Commande
    fi_order = fields.Boolean(string="COMMANDE")
    fi_order_client = fields.Boolean(string="Client")
    fi_order_name = fields.Boolean(string=u"Commande associée")  # doublons ?
    fi_order_confirmation_date = fields.Boolean(string="Date de confirmation")
    fi_order_interv_label = fields.Boolean(string=u"Libellé")  # doublons ?
    fi_order_company = fields.Boolean(string="Magasin")
    fi_order_seller = fields.Boolean(string="Vendeur")
    # -- FI - Articles
    fi_products = fields.Boolean(string="ARTICLES")
    fi_products_order = fields.Boolean(string="Lignes de commande")
    fi_products_picking = fields.Boolean(string="Lignes de BL")
    # -- FI - Rdv d'intervention
    fi_rdv = fields.Boolean(string="INTERVENTION")
    fi_rdv_date_start = fields.Boolean(string=u"Date de début")
    fi_rdv_date_end = fields.Boolean(string="Date de fin")
    fi_rdv_task = fields.Boolean(string=u"Tâche")
    fi_rdv_task_description = fields.Boolean(string=u"Description tâche")
    fi_rdv_duration = fields.Boolean(string=u"Durée")
    fi_rdv_tech = fields.Boolean(string="Technicien(s)")
    fi_rdv_address = fields.Boolean(string="Adresse d'intervention")
    fi_rdv_mail = fields.Boolean(string="E-mail")
    fi_rdv_phone = fields.Boolean(string=u"Téléphone")
    # -- FI - Descriptions
    fi_description = fields.Boolean(string="DESCRIPTION(S)")
    fi_description_ext = fields.Boolean(string="Description externe")
    # -- FI - Facturation
    fi_invoicing = fields.Boolean(string="FACTURATION")
    fi_invoicing_ht = fields.Boolean(string="Total HT")
    fi_invoicing_taxes = fields.Boolean(string="Taxes")
    fi_invoicing_ttc = fields.Boolean(string="Total TTC")
    # -- FI - Documents joints
    fi_order_pdf = fields.Boolean(string="Commande")
    fi_picking_pdf = fields.Boolean(string="Bon(s) de livraison(s)")
    fi_invoice_pdf = fields.Boolean(string="Facture(s)")
    # fi_purchase_pdf = fields.Boolean(string="Achat(s)")
    fi_mail_template_ids = fields.Many2many(
        comodel_name='of.mail.template', relation='fi_intervention_mail_template', string="Documents joints")

    # Rapport d'intervention
    ri_default = fields.Boolean(string=u"Rapport par défaut", default=True)
    ri_title = fields.Char(string="Titre du rapport", default="Rapport d'intervention")
    # -- RI - Rdv d'intervention
    ri_rdv = fields.Boolean(string="INTERVENTION")
    ri_rdv_lib = fields.Boolean(string=u"Libellé de l'intervention")
    ri_rdv_tech = fields.Boolean(string="Technicien")
    ri_rdv_date_start = fields.Boolean(string=u"Date de début")
    ri_rdv_date_end = fields.Boolean(string="Date de fin")
    ri_rdv_duration = fields.Boolean(string=u"Durée")
    ri_rdv_task = fields.Boolean(string=u"Tâche")
    ri_rdv_task_description = fields.Boolean(string=u"Description tâche")
    # -- RI - Facturation
    ri_origin = fields.Boolean(string="ORIGINE")
    # -- RI - Facturation
    ri_invoicing = fields.Boolean(string="FACTURATION")
    # -- RI - Notes
    ri_notes = fields.Boolean(string="NOTES")
    ri_notes_desc = fields.Boolean(string="Description intervention")
    # -- RI - Documents joints
    ri_order_pdf = fields.Boolean(string="Commande")
    ri_picking_pdf = fields.Boolean(string="Bon(s) de livraison(s)")
    ri_invoice_pdf = fields.Boolean(string="Facture(s)")
    # fi_purchase_pdf = fields.Boolean(string="Achat(s)")
    ri_mail_template_ids = fields.Many2many(
        comodel_name='of.mail.template', relation='ri_intervention_mail_template', string="Documents joints")
    # -- RI - Mentions légales
    legal = fields.Text(string=u"Mentions légales")
    ri_legal = fields.Boolean(string=u"MENTIONS LÉGALES")

    @api.depends()
    def _compute_is_default_template(self):
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        if default_template:
            default_template.is_default_template = True

    @api.depends('sequence_id')
    def _compute_code(self):
        for template in self:
            template.code = template.sequence_id.prefix

    def _inverse_code(self):
        sequence_obj = self.env['ir.sequence']
        for template in self:
            if not template.code:
                continue
            sequence_name = u"Modèle d'intervention " + template.code
            sequence_code = self._name
            # Si une séquence existe déjà avec ce code, on la reprend
            sequence = sequence_obj.search([('code', '=', sequence_code), ('prefix', '=', self.code)])
            if sequence:
                template.sequence_id = sequence
                continue

            if template.sequence_id:
                # Si la séquence n'est pas utilisée par un autre modèle, on la modifie directement,
                # sinon il faudra en re-créer une.
                if not self.search([('sequence_id', '=', template.sequence_id.id), ('id', '!=', template.id)]):
                    template.sequence_id.sudo().write({'prefix': template.code, 'name': sequence_name})
                    continue

            # Création d'une séquence pour le modèle
            sequence_data = {
                'name': sequence_name,
                'code': sequence_code,
                'implementation': 'no_gap',
                'prefix': template.code,
                'padding': 4,
                }
            template.sequence_id = self.env['ir.sequence'].sudo().create(sequence_data)

    @api.onchange('fi_default')
    def _onchange_ri_default(self):
        if self.fi_default:
            self.update(self._get_default_template_values_fi())

    @api.onchange('ri_default')
    def _onchange_ri_default(self):
        if self.ri_default:
            self.update(self._get_default_template_values_ri())

    @api.model
    def create(self, vals):
        if vals.get('fi_default', False):
            vals.update(self._get_default_template_values_fi())
        if vals.get('ri_default', False):
            vals.update(self._get_default_template_values_ri())
        return super(OfPlanningInterventionTemplate, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('fi_default', False):
            vals.update(self._get_default_template_values_fi())
        if vals.get('ri_default', False):
            vals.update(self._get_default_template_values_ri())
        res = super(OfPlanningInterventionTemplate, self).write(vals)
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        if default_template and default_template in self:
            others = self.search([('id', '!=', default_template.id), ('fi_default', '=', True)])
            others.write(self._get_default_template_values_fi())
            others = self.search([('id', '!=', default_template.id), ('ri_default', '=', True)])
            others.write(self._get_default_template_values_ri())
        return res

    @api.multi
    def unlink(self):
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        if default_template and default_template in self:
            raise UserError(u"Impossible de supprimer le modèle d'intervention par défaut")
        res = super(OfPlanningInterventionTemplate, self).unlink()
        return res

    @api.multi
    def get_fi_mail_template_data(self, rdv):
        self.ensure_one()
        compose_mail_obj = self.env['of.compose.mail']
        attachment_obj = self.env['ir.attachment']
        data = []
        for mail_template in self.fi_mail_template_ids:
            if mail_template.file:
                # Utilisation des documents pdf fournis
                if not mail_template.chp_ids:
                    data.append(mail_template.file)
                    continue
                # Calcul des champs remplis sur le modèle de courrier
                attachment = attachment_obj.search([('res_model', '=', mail_template._name),
                                                    ('res_field', '=', 'file'),
                                                    ('res_id', '=', mail_template.id)])
                datas = dict(compose_mail_obj.eval_champs(rdv, mail_template.chp_ids))
                file_path = attachment_obj._full_path(attachment.store_fname)
                fd, generated_pdf = tempfile.mkstemp(prefix='doc_joint_', suffix='.pdf')
                try:
                    pypdftk.fill_form(file_path, datas, out_file=generated_pdf, flatten=not mail_template.fillable)
                    with open(generated_pdf, "rb") as encode:
                        encoded_file = base64.b64encode(encode.read())
                finally:
                    os.close(fd)
                    try:
                        os.remove(generated_pdf)
                    except Exception:
                        pass
                data.append(encoded_file)
        return data

    @api.multi
    def get_fi_internal_docs(self, rdv):
        self.ensure_one()
        report_obj = self.env['report']
        data = []
        # order : sale.report_saleorder
        # invoice : account.report_invoice
        # picking : stock.report_deliveryslip
        if rdv.order_id and self.fi_order_pdf:
            data.append(base64.b64encode(report_obj.get_pdf([rdv.order_id.id], 'sale.report_saleorder')))
        if rdv.picking_id and self.fi_picking_pdf:
            data.append(base64.b64encode(report_obj.get_pdf([rdv.picking_id.id], 'stock.report_deliveryslip')))
        if rdv.invoice_ids and self.fi_invoice_pdf:
            data.append(base64.b64encode(report_obj.get_pdf(rdv.invoice_ids.ids, 'account.report_invoice')))
        return data

    @api.multi
    def fi_doc_joints(self, rdv):
        self.ensure_one()
        return self.get_fi_mail_template_data(rdv) + self.get_fi_internal_docs(rdv)

    @api.multi
    def get_ri_mail_template_data(self, rdv):
        self.ensure_one()
        compose_mail_obj = self.env['of.compose.mail']
        attachment_obj = self.env['ir.attachment']
        data = []
        for mail_template in self.ri_mail_template_ids:
            if mail_template.file:
                # Utilisation des documents pdf fournis
                if not mail_template.chp_ids:
                    data.append(mail_template.file)
                    continue
                # Calcul des champs remplis sur le modèle de courrier
                attachment = attachment_obj.search([('res_model', '=', mail_template._name),
                                                    ('res_field', '=', 'file'),
                                                    ('res_id', '=', mail_template.id)])
                datas = dict(compose_mail_obj.eval_champs(rdv, mail_template.chp_ids))
                file_path = attachment_obj._full_path(attachment.store_fname)
                fd, generated_pdf = tempfile.mkstemp(prefix='doc_joint_', suffix='.pdf')
                try:
                    pypdftk.fill_form(file_path, datas, out_file=generated_pdf, flatten=not mail_template.fillable)
                    with open(generated_pdf, "rb") as encode:
                        encoded_file = base64.b64encode(encode.read())
                finally:
                    os.close(fd)
                    try:
                        os.remove(generated_pdf)
                    except Exception:
                        pass
                data.append(encoded_file)
        return data

    @api.multi
    def get_ri_internal_docs(self, rdv):
        self.ensure_one()
        report_obj = self.env['report']
        data = []
        # order : sale.report_saleorder
        # invoice : account.report_invoice
        # picking : stock.report_deliveryslip
        if rdv.order_id and self.ri_order_pdf:
            data.append(base64.b64encode(report_obj.get_pdf([rdv.order_id.id], 'sale.report_saleorder')))
        if rdv.picking_id and self.ri_picking_pdf:
            data.append(base64.b64encode(report_obj.get_pdf([rdv.picking_id.id], 'stock.report_deliveryslip')))
        if rdv.invoice_ids and self.ri_invoice_pdf:
            data.append(base64.b64encode(report_obj.get_pdf(rdv.invoice_ids.ids, 'account.report_invoice')))
        return data

    @api.multi
    def ri_doc_joints(self, rdv):
        self.ensure_one()
        return self.get_ri_mail_template_data(rdv) + self.get_ri_internal_docs(rdv)


class OfPlanningInterventionTemplateLine(models.Model):
    _name = 'of.planning.intervention.template.line'

    template_id = fields.Many2one('of.planning.intervention.template', string=u"Modèle", required=True)
    product_id = fields.Many2one('product.product', string='Article')
    price_unit = fields.Float(string='Prix unitaire', digits=dp.get_precision('Product Price'), default=0.0)
    qty = fields.Float(string=u'Qté', digits=dp.get_precision('Product Unit of Measure'))
    name = fields.Text(string='Description')

    @api.onchange('product_id')
    def _onchange_product(self):
        product = self.product_id
        self.qty = 1
        self.price_unit = product.lst_price
        if product:
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
        else:
            self.name = ''

    @api.multi
    def get_intervention_line_values(self):
        self.ensure_one()
        return {
            'product_id': self.product_id,
            'price_unit': self.price_unit,
            'qty': self.qty,
            'name': self.name,
            }


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    # Surcharge pour permettre la progagation des informations du modèle d'intervention par défaut
    # vers les autres modèles existants
    @api.model
    def _update(self, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False):
        res = super(IrModelData, self)._update(
                model=model, module=module, values=values, xml_id=xml_id, store=store, noupdate=noupdate, mode=mode,
                res_id=res_id)
        if xml_id == 'of_planning_default_intervention_template':
            template_obj = self.env['of.planning.intervention.template']
            default_template = self.env.ref(
                    'of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
            if default_template:
                others = template_obj.search([('id', '!=', default_template.id), ('fi_default', '=', True)])
                others.write(template_obj._get_default_template_values_fi())
                others = template_obj.search([('id', '!=', default_template.id), ('ri_default', '=', True)])
                others.write(template_obj._get_default_template_values_ri())
        return res
