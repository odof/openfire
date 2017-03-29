# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_objects(self, o):
        result = super(OfComposeMail,self)._get_objects(o)
        if o._name == 'of.planning.intervention':
            result.update({
                'interventions': [o],
                'partner'      : o.part_id or False,
                'address'      : o.address_id or False,
                'shop'         : o.company_id,
                # order_id et invoice_id ne seront définis que dans of_sales, mais getattr gère l'exception si le module n'est pas installé
                'order'        : getattr(o, 'order_id', False),
                'invoice'      : getattr(o, 'invoice_id', False),
            })
        else:
            # interventions_liees ne sera défini que dans of_sales, mais getattr gère l'exception si le module n'est pas installé
            result['interventions'] = getattr(o, 'interventions_liees', [])
        return result

    @api.model
    def _get_dict_values(self, o, objects=None):
        if not objects:
            objects = self._get_objects(o)
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        result = super(OfComposeMail,self)._get_dict_values(o, objects=objects)

        equipes = []
        dates = []

        for intervention in objects['interventions']:
            equipes.append(intervention.equipe_id.name)
            d_interv = fields.Datetime.from_string(intervention.date)
            d_interv = fields.Datetime.context_timestamp(self, d_interv)

            dates.append(d_interv.strftime("%d/%m/%Y à %H:%M"))

        tache_product_ttc = ''
        duree = ''
        intervention = objects['interventions']
        if intervention:
            intervention = intervention[0]
            h = int(intervention.duree)
            m = 60 * (intervention.duree - h)
            duree = "%02d:%02d" % (h,m)

            if intervention.tache_id.product_id:
                tache_product_ht = intervention.tache_id.product_id.list_pvht or 0.0
                fpos = False
                partner = objects['partner']
                if partner:
                    fpos = partner.property_account_position or False
                    if not fpos:
                        fpos = partner.company_id and partner.company_id.fiscal_position_sale or False
                if fpos:
                    tache_product_tax = 0.0
                    for tax in fpos.tax_ids:
                        tache_product_tax += tax.tax_src_id.amount

                    lang_obj = self.env['res.lang']
                    lang_code = self._context.get('lang', partner.lang)
                    lang = lang_obj.search([('code','=', lang_code)], limit=1)
                    tache_product_ttc = lang.format("%.2f", round(tache_product_ht * (1.0 + tache_product_tax), 2), grouping=True)

        result.update({
            'date_intervention': dates and dates[0] or ' ',
            'date_intervention_date': dates and dates[0].split()[0] or ' ',
            'equipe': equipes and equipes[0] or '',
            'equipes': "\n".join(equipes),
            'dates_intervention': "\n".join(dates),
            'duree_intervention': duree,
            'tache': intervention and intervention.tache_id and intervention.tache_id.name or '',
            'tache_product_ttc': tache_product_ttc,
        })
        # Pour rétrocompatibilité
        result.update({
            'date_pose': result['date_intervention'],
            'date_pose_date': result['date_intervention_date'],
            'equipe_pose': result['equipe'],
            'equipe_poses': result['equipes'],
            'date_poses': result['dates_intervention'],
            'duree_pose': result['duree_intervention'],
            'tache_pose': result['tache'],
            'tache_product_ttc': tache_product_ttc,
        })
        return result

    def _get_model_action_dict(self):
        result = super(OfComposeMail, self)._get_model_action_dict()
        result['of.planning.pose'] = 'of_planning.courriers_pose'
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
