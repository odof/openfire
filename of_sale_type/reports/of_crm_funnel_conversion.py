# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, tools


class OFCRMFunnelConversion(models.Model):
    _inherit = "of.crm.funnel.conversion"

    sale_type_id = fields.Many2one(comodel_name='of.sale.type', string=u"Type de devis", readonly=True)

    @api.model_cr
    def init(self):
        """Inject parts in the query with this hack, fetching the query and
        recreating it. Query is returned all in upper case and with final ';'.
        """
        super(OFCRMFunnelConversion, self).init()
        self._cr.execute("SELECT pg_get_viewdef(%s, true)", (self._table,))
        view_def = self._cr.fetchone()[0]
        if view_def[-1] == ';':  # Remove trailing semicolon
            view_def = view_def[:-1]

        view_def = view_def.replace(
            'COALESCE(so1.of_canvasser_id, so2.of_canvasser_id) AS canvasser_id,',
            'COALESCE(SO1.of_canvasser_id, SO2.of_canvasser_id) AS canvasser_id,\n'
            'COALESCE(SO1.of_sale_type_id, SO2.of_sale_type_id) AS sale_type_id,')
        view_def = view_def.replace(
            ', so2.of_canvasser_id',
            ', so2.of_canvasser_id, so1.of_sale_type_id, so2.of_sale_type_id')
        view_def = view_def.replace(
            'NULL::integer AS canvasser_id,',
            'NULL::integer AS canvasser_id,\n'
            'NULL::integer AS sale_type_id,')

        # Re-create view
        tools.drop_view_if_exists(self._cr, self._table)
        # pylint: disable=sql-injection
        self._cr.execute("create or replace view {} as ({})".format(self._table, view_def))


class OFCRMFunnelConversion2(models.Model):
    _inherit = "of.crm.funnel.conversion2"

    sale_type_id = fields.Many2one(comodel_name='of.sale.type', string=u"Type de devis", readonly=True)

    @api.model_cr
    def init(self):
        """Inject parts in the query with this hack, fetching the query and
        recreating it. Query is returned all in upper case and with final ';'.
        """
        super(OFCRMFunnelConversion2, self).init()
        self._cr.execute("SELECT pg_get_viewdef(%s, true)", (self._table,))
        view_def = self._cr.fetchone()[0]
        if view_def[-1] == ';':  # Remove trailing semicolon
            view_def = view_def[:-1]

        view_def = view_def.replace(
            't.canvasser_id,',
            't.canvasser_id, t.sale_type_id,')
        view_def = view_def.replace(
            'cl.of_prospecteur_id AS canvasser_id,',
            'cl.of_prospecteur_id AS canvasser_id,\n'
            'NULL::integer AS sale_type_id,')
        view_def = view_def.replace(
            'so.of_canvasser_id AS canvasser_id,',
            'so.of_canvasser_id AS canvasser_id,\n'
            'so.of_sale_type_id AS sale_type_id,')
        view_def = view_def.replace(
            'so.of_canvasser_id,',
            'so.of_canvasser_id, so.of_sale_type_id,')
        view_def = view_def.replace(
            'so2.of_canvasser_id AS canvasser_id,',
            'so2.of_canvasser_id AS canvasser_id,\n'
            'so2.of_sale_type_id AS sale_type_id,')
        view_def = view_def.replace(
            'so2.of_canvasser_id,',
            'so2.of_canvasser_id, so2.of_sale_type_id,')
        view_def = view_def.replace(
            'cl4.of_prospecteur_id AS canvasser_id,',
            'cl4.of_prospecteur_id AS canvasser_id,\n'
            'NULL::integer AS sale_type_id,')
        view_def = view_def.replace(
            'NULL::integer AS canvasser_id,',
            'NULL::integer AS canvasser_id,\n'
            'NULL::integer AS sale_type_id,')

        # Re-create view
        tools.drop_view_if_exists(self._cr, self._table)
        # pylint: disable=sql-injection
        self._cr.execute("create or replace view {} as ({})".format(self._table, view_def))
