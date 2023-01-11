# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

STEP_NAME_NUMBER = {
    'new': 0,
    'vendor_select': 10,
    'customer_details': 20,
    'quote_details': 30,
    'product_select': 40,
    'product_details': 50,
    'product_accessories': 60,
    'all_accessories': 60,
    'quote_summary': 70,
}


class OFWebsiteWorktopConfigurator(http.Controller):

    def get_redirection(self, step):
        # L'utilisateur n'est pas connecté -> on le redirige sur la page de connexion
        if request.env.uid == request.website.user_id.id:
            return request.redirect('/web/login')
        # Si le champ worktop_quote_id est renseigné, mais que la commande correspondante est supprimée,
        # on retourne au début du configurateur
        if request.session.get('worktop_quote_id'):
            quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
            if not quote.exists():
                request.session.pop('worktop_quote_id', None)
                request.session.pop('worktop_quote_line_id', None)
                return request.redirect('/worktop_configurator/vendor_select')
        step_number = STEP_NAME_NUMBER[step] or 0
        if step_number > 10 and not request.session.get('vendor_address_id'):
            return request.redirect('/worktop_configurator/vendor_select')
        if step_number > 20 and not request.session.get('customer_address_id'):
            return request.redirect('/worktop_configurator/customer_details')
        if step_number > 30 and not request.session.get('worktop_quote_id'):
            return request.redirect('/worktop_configurator/quote_details')
        if step_number == 50 and not request.session.get('product_type_id'):
            return request.redirect('/worktop_configurator/product_select')
        return False

    @http.route(['/worktop_configurator'], type='http', auth='user', website=True)
    def worktop_configurator(self, **kw):
        current_step = 'new'

        # On vide les variables de session
        self._empty_session()

        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        return request.redirect('/worktop_configurator/vendor_select')

    @http.route(['/worktop_configurator/vendor_select'], type='http', auth='user', website=True)
    def worktop_configurator_vendor_select(self, **kw):
        current_step = 'vendor_select'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        # Si utilisateur portail, on redirige automatiquement à l'étape suivante
        if not request.env.user.has_group('base.group_user'):
            request.session['portal_user'] = True
            request.session['vendor_address_id'] = request.env.user.partner_id.id
            return request.redirect('/worktop_configurator/customer_details')

        values = kw
        error = dict()

        # Le formulaire a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            # Champs obligatoires
            if not values.get('vendor_address_id'):
                error['vendor_address_id'] = True

            if not error:
                request.session['vendor_address_id'] = int(values['vendor_address_id'])

                # On teste si le devis a déjà été généré pour MAJ (cas d'un retour arrière dans le process)
                if request.session.get('worktop_quote_id'):
                    quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])

                    if quote.partner_id.id != request.session['vendor_address_id']:

                        # On force la société du site web pour obtenir la liste de prix
                        pricelist_obj = request.env['product.pricelist']
                        pricelist_id = pricelist_obj._get_partner_pricelist(
                            partner_id=request.env['res.partner'].browse(
                                request.session['vendor_address_id']).commercial_partner_id.id,
                            company_id=request.website.company_id.id)
                        pricelist = pricelist_obj.browse(pricelist_id)

                        quote.write({'partner_id': request.session['vendor_address_id'],
                                     'pricelist_id': pricelist.id})

                return request.redirect('/worktop_configurator/customer_details')

        values['error_dict'] = error

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)
        values['vendors'] = request.env['res.partner'].search([('of_worktop_configurator_contact', '=', True)])
        values['vendor_address_id'] = values.get('vendor_address_id') or request.session.get('vendor_address_id')

        return request.render('of_website_worktop_configurator.worktop_configurator_vendor_select', values)

    @http.route(['/worktop_configurator/customer_details'], type='http', auth='user', website=True)
    def worktop_configurator_customer_details(self, **kw):
        current_step = 'customer_details'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()

        # Le formulaire a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            # Champs obligatoires
            if not values.get('name'):
                error['name'] = True
            if not values.get('street'):
                error['street'] = True
            if not values.get('zip'):
                error['zip'] = True
            if not values.get('city'):
                error['city'] = True
            if not values.get('country_id'):
                error['country_id'] = True
            if not values.get('invoicing_recipient') and request.env.user.has_group('base.group_user'):
                error['invoicing_recipient'] = True
            elif values.get('invoicing_recipient') == 'customer' or not request.env.user.has_group('base.group_user'):
                if not values.get('different_invoicing_address'):
                    error['different_invoicing_address'] = True
                elif values.get('different_invoicing_address') == 'yes':
                    if not values.get('invoicing_street'):
                        error['invoicing_street'] = True
                    if not values.get('invoicing_zip'):
                        error['invoicing_zip'] = True
                    if not values.get('invoicing_city'):
                        error['invoicing_city'] = True
                    if not values.get('invoicing_country_id'):
                        error['invoicing_country_id'] = True
            elif values.get('invoicing_recipient') == 'vendor':
                if values.get('create_vendor_address') == 'yes' or values.get('update_vendor_address') == 'yes':
                    if not values.get('invoicing_street'):
                        error['invoicing_street'] = True
                    if not values.get('invoicing_zip'):
                        error['invoicing_zip'] = True
                    if not values.get('invoicing_city'):
                        error['invoicing_city'] = True
                    if not values.get('invoicing_country_id'):
                        error['invoicing_country_id'] = True

            if not error:
                vals = {}
                # Adresse de chantier
                # Si l'adresse de chantier existe déjà et n'est pas déjà présente
                # en adresse de livraison d'une autre commande
                new_address = False
                if request.session.get('customer_address_id'):
                    new_address = self._update_customer_address(request.session['customer_address_id'])
                if not request.session.get('customer_address_id') or new_address:
                    customer_address_id = self._create_customer_address()
                    request.session['customer_address_id'] = customer_address_id
                    vals['partner_shipping_id'] = customer_address_id

                # Adresse de facturation
                request.session['invoicing_recipient'] = values.get('invoicing_recipient')
                if values.get('invoicing_recipient') == 'customer' or not request.env.user.has_group('base.group_user'):
                    request.session['different_invoicing_address'] = values['different_invoicing_address']
                    if values.get('different_invoicing_address') == 'yes':
                        if request.session.get('customer_invoicing_address_id') == \
                                request.session.get('customer_address_id'):
                            request.session.pop('customer_invoicing_address_id', None)
                        new_address = False
                        if request.session.get('customer_invoicing_address_id'):
                            new_address = self._update_invoicing_address(
                                request.session['customer_invoicing_address_id'])
                        if not request.session.get('customer_invoicing_address_id') or new_address:
                            invoicing_address_id = self._create_invoicing_address(
                                request.session['customer_address_id'])
                            request.session['customer_invoicing_address_id'] = invoicing_address_id
                            vals['partner_invoice_id'] = invoicing_address_id
                else:
                    request.session.pop('different_invoicing_address', None)
                    if values.get('create_vendor_address') == 'yes':
                        invoicing_address_id = self._create_invoicing_address(request.session['vendor_address_id'])
                        request.session['vendor_invoicing_address_id'] = invoicing_address_id
                    elif values.get('update_vendor_address') == 'yes':
                        self._update_invoicing_address(request.session['vendor_invoicing_address_id'], vendor=True)

                # Si le devis a déjà été généré, on met à jour l'adresse de facturation si besoin
                if request.session.get('worktop_quote_id'):
                    quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
                    if values.get('invoicing_recipient') == 'vendor' and \
                            quote.partner_invoice_id.id != request.session['vendor_invoicing_address_id']:
                        vals['partner_invoice_id'] = request.session['vendor_invoicing_address_id']
                    elif (values.get('invoicing_recipient') == 'customer' or
                          not request.env.user.has_group('base.group_user')) and \
                            values.get('different_invoicing_address') == 'yes' and \
                            quote.partner_invoice_id.id != request.session['customer_invoicing_address_id']:
                        vals['partner_invoice_id'] = request.session['customer_invoicing_address_id']
                    elif (values.get('invoicing_recipient') == 'customer' or
                          not request.env.user.has_group('base.group_user')) and \
                            values.get('different_invoicing_address') == 'no' and \
                            quote.partner_invoice_id.id != request.session['customer_address_id']:
                        vals['partner_invoice_id'] = request.session['customer_address_id']

                    if vals:
                        quote.write(vals)

                return request.redirect('/worktop_configurator/quote_details')

        values['error_dict'] = error

        # Une adresse différente a été sélectionnée -> pas de nouveau rendu mais MAJ session
        if values.get('vendor_invoicing_address_id') and values.get('xhr'):
            request.session['vendor_invoicing_address_id'] = int(values['vendor_invoicing_address_id'])
            return 'ok'

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)
        partner_obj = request.env['res.partner'].sudo()
        customer_address = partner_obj
        if request.session.get('customer_address_id'):
            customer_address = partner_obj.browse(request.session['customer_address_id'])

        values['name'] = values.get('name') or customer_address.name
        values['email'] = values.get('email') or customer_address.email
        values['phone'] = values.get('phone') or customer_address.phone
        values['street'] = values.get('street') or customer_address.street
        values['street2'] = values.get('street2') or customer_address.street2
        values['zip_code'] = values.get('zip') or customer_address.zip
        values['city'] = values.get('city') or customer_address.city
        values['country'] = values.get('country_id') and request.env['res.country'].browse(int(values['country_id'])) \
            or customer_address.country_id or request.env['res.country'].search([('name', '=', u"France")], limit=1)
        values['country_list'] = request.env['res.country'].search([])

        values['portal_user'] = not request.env.user.has_group('base.group_user')
        values['invoicing_recipient'] = values.get('invoicing_recipient') or request.session.get('invoicing_recipient')
        values['different_invoicing_address'] = values.get('different_invoicing_address') or \
            request.session.get('different_invoicing_address')

        if (values.get('invoicing_recipient') == 'customer' or not request.env.user.has_group('base.group_user')) and \
                request.session.get('customer_invoicing_address_id'):
            invoicing_address = partner_obj.browse(request.session['customer_invoicing_address_id'])

            values['invoicing_name'] = values.get('invoicing_name') or invoicing_address.name
            values['invoicing_email'] = values.get('invoicing_email') or invoicing_address.email
            values['invoicing_phone'] = values.get('invoicing_phone') or invoicing_address.phone
            values['invoicing_street'] = values.get('invoicing_street') or invoicing_address.street
            values['invoicing_street2'] = values.get('invoicing_street2') or invoicing_address.street2
            values['invoicing_zip_code'] = values.get('invoicing_zip') or invoicing_address.zip
            values['invoicing_city'] = values.get('invoicing_city') or invoicing_address.city
            values['invoicing_country'] = values.get('invoicing_country_id') and \
                request.env['res.country'].browse(int(values['invoicing_country_id'])) or \
                invoicing_address.country_id or request.env['res.country'].search([('name', '=', u"France")], limit=1)
        else:
            values['invoicing_zip_code'] = values.get('invoicing_zip')
            values['invoicing_country'] = values.get('invoicing_country_id') and \
                request.env['res.country'].browse(int(values['invoicing_country_id'])) or \
                request.env['res.country'].search([('name', '=', u"France")], limit=1)

        vendor = request.env['res.partner'].browse(request.session.get('vendor_address_id'))
        values['vendor_addresses'] = request.env['res.partner'].search(
            [('id', 'child_of', vendor.commercial_partner_id.id)])
        values['vendor_invoicing_address_id'] = request.session.get('vendor_invoicing_address_id') or vendor.id
        request.session['vendor_invoicing_address_id'] = values['vendor_invoicing_address_id']
        values['create_vendor_address'] = values.get('create_vendor_address') or "no"
        values['update_vendor_address'] = values.get('update_vendor_address') or "no"

        values['portal_user'] = request.session.get('portal_user')

        return request.render('of_website_worktop_configurator.worktop_configurator_customer_details', values)

    @http.route(['/worktop_configurator/quote_details'], type='http', auth='user', website=True)
    def worktop_configurator_quote_details(self, **kw):
        current_step = 'quote_details'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()

        # Le formulaire a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            # Champs obligatoires
            if not values.get('fiscal_pos_id'):
                error['fiscal_pos_id'] = True
            if not values.get('delivery_floor'):
                error['delivery_floor'] = True
            if not values.get('site_service_id'):
                error['site_service_id'] = True
            if not values.get('junction'):
                error['junction'] = True
            # Contrôle de l'étage
            error_message = []
            # Contrôle de la prestation bloquante
            if values.get('site_service_id'):
                site_service = request.env['of.worktop.configurator.service'].browse(int(values['site_service_id']))
                if site_service.blocking:
                    error['site_service_id'] = True
                    error_message.append(site_service.blocking_message)

            if error:
                error['error_message'] = error_message
            else:
                if request.session.get('worktop_quote_id'):
                    self._update_quote(request.session['worktop_quote_id'])
                else:
                    quote_id = self._create_quote()
                    request.session['worktop_quote_id'] = quote_id
                return request.redirect('/worktop_configurator/product_select')

        values['error_dict'] = error

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)
        sale_order_obj = request.env['sale.order'].sudo()
        quote = sale_order_obj
        if request.session.get('worktop_quote_id'):
            quote = sale_order_obj.browse(request.session['worktop_quote_id'])

        values['ref'] = values.get('ref') or quote.client_order_ref
        values['delivery_expected_date'] = values.get('delivery_expected_date') or quote.of_date_de_pose
        values['delivery_floor'] = values.get('delivery_floor') or (
                quote and (quote.of_delivery_floor and 'yes' or 'no'))
        values['junction'] = values.get('junction') or (quote and (quote.of_junction and 'yes' or 'no'))

        # On restreint les positions fiscales en fonction de la liste de prix
        # On force la société du site web pour obtenir la liste de prix
        pricelist_obj = request.env['product.pricelist']
        pricelist_id = pricelist_obj._get_partner_pricelist(
            partner_id=request.env['res.partner'].browse(request.session['vendor_address_id']).commercial_partner_id.id,
            company_id=request.website.company_id.id)
        pricelist = pricelist_obj.browse(pricelist_id)

        values['fiscal_pos'] = values.get('fiscal_pos_id') and \
            request.env['account.fiscal.position'].sudo().browse(int(values['fiscal_pos_id'])) or \
            quote.fiscal_position_id
        values['fiscal_pos_list'] = request.env['of.worktop.configurator.tax'].sudo().search(
            [('pricelist_ids', 'in', pricelist.id)]).mapped('fiscal_position_id')

        values['site_service'] = values.get('site_service_id') and \
            request.env['of.worktop.configurator.service'].browse(int(values['site_service_id'])) or \
            quote.of_site_service_id
        values['site_service_list'] = request.env['of.worktop.configurator.service'].search([])

        return request.render('of_website_worktop_configurator.worktop_configurator_quote_details', values)

    @http.route(['/worktop_configurator/product_select'], type='http', auth='user', website=True)
    def worktop_configurator_product_select(self, **kw):
        current_step = 'product_select'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw

        # Le formulaire a été soumis -> traitement
        if 'submitted' in values:
            # Cas du bouton Accessoires
            if values['product_type_id'] == "Accessoires":
                request.session.pop('product_type_id', None)
                return request.redirect('/worktop_configurator/all_accessories')
            else:
                request.session['product_type_id'] = int(values['product_type_id'])
                return request.redirect('/worktop_configurator/product_details')

        # Arrivée sur la page
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)
        values['product_types'] = request.env['of.worktop.configurator.type'].search([])

        # On regarde si le devis contient déjà un type de pièce pour afficher le bouton de redirection
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        if quote.order_line.filtered(lambda l: l.product_id.id in values['product_types'].mapped('product_id').ids):
            values['display_redirect_button'] = True
        else:
            values['display_redirect_button'] = False

        return request.render('of_website_worktop_configurator.worktop_configurator_product_select', values)

    @http.route(['/worktop_configurator/product_details'], type='http', auth='user', website=True)
    def worktop_configurator_product_details(self, **kw):
        current_step = 'product_details'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()

        # Le formulaire a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            # Champs obligatoires
            if not values.get('material_id'):
                error['material_id'] = True
            if not values.get('finishing_id'):
                error['finishing_id'] = True
            if not values.get('color_id'):
                error['color_id'] = True
            if not values.get('length'):
                error['length'] = True
            if not values.get('width'):
                error['width'] = True
            if not values.get('thickness_id'):
                error['thickness_id'] = True
            # Contrôle des float:
            error_message = []
            if values.get('length'):
                try:
                    float(values['length'].replace(',', '.'))
                except ValueError:
                    error['length'] = True
                    error_message.append(u"La longueur indiquée ne correspond pas à un nombre valide.")
            if values.get('width'):
                try:
                    float(values['width'].replace(',', '.'))
                except ValueError:
                    error['width'] = True
                    error_message.append(u"La largeur indiquée ne correspond pas à un nombre valide.")

            if error:
                error['error_message'] = error_message
            else:
                if request.session.get('worktop_quote_line_id'):
                    self._update_quote_line(request.session['worktop_quote_line_id'])
                else:
                    quote_line_id = self._create_quote_line()
                    request.session['worktop_quote_line_id'] = quote_line_id
                self._control_weight()
                self._compute_discount()
                return request.redirect('/worktop_configurator/product_accessories')

        values['error_dict'] = error

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        product_type = request.env['of.worktop.configurator.type'].browse(request.session['product_type_id'])

        values['material_id'] = values.get('material_id') or request.session.get('material_id')
        values['material_list'] = product_type.material_ids
        values['finishing_id'] = values.get('finishing_id') or request.session.get('finishing_id')
        values['finishing_list'] = product_type.finishing_ids
        values['color_id'] = values.get('color_id') or request.session.get('color_id')
        values['color_list'] = request.env['of.worktop.configurator.color'].search([])
        values['length'] = round(values.get('length'), 2) if values.get('length') else request.session.get('length')
        values['width'] = round(values.get('width'), 2) if values.get('width') else request.session.get('width')
        values['thickness_id'] = values.get('thickness_id') or request.session.get('thickness_id')
        values['thickness_list'] = request.env['of.worktop.configurator.thickness'].search([])
        values['type_name'] = product_type.name
        values['currency'] = quote.currency_id
        values['price'] = values.get('price') or request.session.get('product_price') and \
            request.session.get('product_price') * self._get_coef() or 0.0
        taxes = product_type.product_id.sudo().taxes_id.filtered(lambda r: r.company_id == request.website.company_id)
        tax_id = quote.fiscal_position_id.map_tax(taxes, product_type.product_id, quote.partner_id)
        values['total_price'] = tax_id.compute_all(values['price'], quote.currency_id, 1.0)['total_included']

        return request.render('of_website_worktop_configurator.worktop_configurator_product_details', values)

    @http.route(['/worktop_configurator/product_accessories',
                 '/worktop_configurator/product_accessories/page/<int:page>'], type='http', auth='user', website=True)
    def worktop_configurator_product_accessories(self, page=0, **kw):
        current_step = 'product_accessories'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        search_criteria = ""

        # Le formulaire a été soumis -> recherche
        if 'submitted' in values:
            values.pop('submitted')
            search_criteria = values.get('search')

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)

        product_line_obj = request.env['of.worktop.configurator.type.product.line']
        product_type = request.env['of.worktop.configurator.type'].browse(request.session['product_type_id'])
        product_lines = product_type.product_line_ids.filtered(
            lambda l: l.material_id.id == request.session['material_id'])
        if not product_lines:
            return request.redirect('/worktop_configurator/quote_summary')
        elif search_criteria:
            product_lines = product_line_obj.search(
                [('id', 'in', product_lines.ids), ('product_name', '=ilike', '%' + search_criteria + '%')])

        # Pager
        ppg = 12
        pager = request.website.pager(
            url='/worktop_configurator/product_accessories', total=len(product_lines), page=page, step=ppg, scope=5)
        product_lines = product_line_obj.search([('id', 'in', product_lines.ids)], limit=ppg, offset=pager['offset'])

        values['product_lines'] = product_lines.sudo()
        values['pager'] = pager

        return request.render('of_website_worktop_configurator.worktop_configurator_product_accessories', values)

    @http.route(['/worktop_configurator/all_accessories',
                 '/worktop_configurator/all_accessories/page/<int:page>'], type='http', auth='user', website=True)
    def worktop_configurator_all_accessories(self, page=0, **kw):
        current_step = 'all_accessories'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        search_criteria = ""

        # Le formulaire a été soumis -> recherche
        if 'submitted' in values:
            values.pop('submitted')
            search_criteria = values.get('search')

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)

        product_obj = request.env['product.product'].sudo()
        accessories = product_obj.search([('of_worktop_configurator_accessory', '=', True)])

        if search_criteria:
            accessories = product_obj.search(
                [('id', 'in', accessories.ids), ('name', '=ilike', '%' + search_criteria + '%')])

        # Pager
        ppg = 12
        pager = request.website.pager(
            url='/worktop_configurator/all_accessories', total=len(accessories), page=page, step=ppg, scope=5)
        accessories = product_obj.search([('id', 'in', accessories.ids)], limit=ppg, offset=pager['offset'])

        values['accessories'] = accessories
        values['pager'] = pager

        return request.render('of_website_worktop_configurator.worktop_configurator_all_accessories', values)

    @http.route(['/worktop_configurator/quote_summary'], type='http', auth='user', website=True)
    def worktop_configurator_quote_summary(self, **kw):
        current_step = 'quote_summary'
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw

        # Le formulaire a été soumis -> validation du devis ou calcul de la remise
        if 'submitted' in values:
            values.pop('submitted')
            quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
            if values.get('action') == 'compute_discount':
                # Calcul de la remise
                quote.of_worktop_configurator_discount_id = request.params.get('discount_id') and \
                    int(request.params.get('discount_id')) or False
                self._compute_discount()
            elif values.get('action') == 'submit':
                # On valide le devis
                quote.write({'state': 'sent',
                             'of_submitted_worktop_configurator_order': True})
                # On abonne le client et les responsables de la même société
                responsibles = request.env['res.partner'].sudo().search(
                    [('id', 'child_of', quote.partner_id.commercial_partner_id.id),
                     ('of_worktop_configurator_responsible', '=', True)])
                quote.message_subscribe(partner_ids=responsibles.ids + [quote.partner_id.id])

                # On vide les variables de session
                self._empty_session()

                # On redirige vers le portail
                return request.redirect('/my/home')

        # Arrivée sur la page
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 0)
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        values['quote'] = quote
        vendor = request.env['res.partner'].sudo().browse(request.session['vendor_address_id'])
        values['vendor'] = vendor

        # On restreint les remises en fonction de la liste de prix
        # On force la société du site web pour obtenir la liste de prix
        pricelist_obj = request.env['product.pricelist']
        pricelist_id = pricelist_obj._get_partner_pricelist(
            partner_id=vendor.commercial_partner_id.id, company_id=request.website.company_id.id)
        pricelist = pricelist_obj.browse(pricelist_id)

        values['discount'] = values.get('discount_id') and \
            request.env['of.worktop.configurator.discount'].browse(int(values['discount_id'])) or \
            quote.of_worktop_configurator_discount_id
        values['discount_list'] = request.env['of.worktop.configurator.discount'].search(
            [('pricelist_ids', 'in', pricelist.id)])

        return request.render('of_website_worktop_configurator.worktop_configurator_quote_summary', values)

    @http.route(['/worktop_configurator/new_product'], type='http', auth='user', website=True)
    def worktop_configurator_new_product(self, **kw):
        # On vide les variables de session
        request.session.pop('product_type_id', None)
        request.session.pop('product_price', None)
        request.session.pop('worktop_quote_line_id', None)
        request.session.pop('thickness_id', None)
        request.session.pop('length', None)
        request.session.pop('width', None)

        # Si les infos de matériaux ne sont pas en session, on essaye de récupérer celles de la dernière pièce créée
        if not request.session.get('material_id') and request.session.get('worktop_quote_id'):
            quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
            quote_lines = quote.order_line.filtered(lambda l: l.of_worktop_configurator_type_id)
            if quote_lines:
                last_line = quote_lines.sorted(key='id', reverse=True)[0]
                request.session['material_id'] = last_line.of_worktop_configurator_material_id.id
                request.session['finishing_id'] = last_line.of_worktop_configurator_finishing_id.id
                request.session['color_id'] = last_line.of_worktop_configurator_color_id.id

        # On redirige vers la page de sélection des types de pièce
        return request.redirect('/worktop_configurator/product_select')

    @http.route(['/worktop_configurator/get_address_field'], type='json', auth='user', website=True)
    def get_address_field(self, address_id):
        address = request.env['res.partner'].browse(int(address_id))
        request.session['vendor_invoicing_address_id'] = int(address_id)
        return {
            'name': address.name or "",
            'email': address.email or "",
            'phone': address.phone or "",
            'street': address.street or "",
            'street2': address.street2 or "",
            'zip': address.zip or "",
            'city': address.city or "",
            'country_id': address.country_id.id,
        }

    @http.route(['/worktop_configurator/get_color_image/<model("of.worktop.configurator.color"):color>'], type='json',
                auth="public", methods=['POST'], website=True)
    def get_color_image(self, color, **kw):
        return dict(image=color.image_file)

    @http.route(['/worktop_configurator/product_modal'], type='json', auth='user', website=True)
    def product_modal(self, product_id, price, **kw):
        product = request.env['product.product'].sudo().browse(int(product_id))

        return request.env['ir.ui.view'].render_template(
            'of_website_worktop_configurator.worktop_configurator_product_modal', {
                'product': product,
                'price': float(price),
            })

    @http.route(['/worktop_configurator/add_product'], type='json', auth='user', website=True)
    def add_product(self, product_id, price, quantity, **kw):
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        acc_layout_category_id = request.env['ir.values'].sudo().get_default(
            'sale.config.settings', 'of_website_worktop_configurator_acc_layout_category_id')
        vals = quote._website_product_id_change(quote.id, int(product_id), qty=float(quantity))
        vals['name'] = quote._get_line_description(quote.id, int(product_id))
        vals['layout_category_id'] = acc_layout_category_id
        vals['price_unit'] = float(price)
        quote_line = request.env['sale.order.line'].sudo().create(vals)
        quote_line.of_no_coef_price = quote_line.price_unit
        quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
        quote_line._compute_tax_id()
        self._compute_discount()
        return True

    @http.route(['/worktop_configurator/quote_line/update_qty'], type='json', auth='user', website=True)
    def update_line_qty(self, line_id, qty):
        quote_line = request.env['sale.order.line'].sudo().browse(line_id)
        quote = quote_line.order_id

        if qty <= 0:
            quote_line.unlink()
            self._control_weight()
        else:
            quote_line.write({'product_uom_qty': qty})

        self._compute_discount()

        return {
            'line_id': quote_line.id,
            'quantity': qty,
            'of_website_worktop_configurator.quote_lines': request.env['ir.ui.view'].render_template(
                'of_website_worktop_configurator.quote_lines', {'quote': quote})
        }

    @http.route(['/worktop_configurator/upload_file'], type='http', auth='user', website=True)
    def worktop_configurator_upload_file(self, **kw):
        values = kw
        if values.get('attachment', False):
            name = values.get('attachment').filename
            order_id = values.get('order_id')
            attachment = values.get('attachment').read()
            request.env['ir.attachment'].sudo().create({
                'name': name,
                'datas_fname': name,
                'res_name': name,
                'type': 'binary',
                'res_model': 'sale.order',
                'res_id': order_id,
                'datas': attachment.encode('base64'),
            })
        return request.redirect('/worktop_configurator/quote_summary')

    @http.route(['/worktop_configurator/get_pricelist'], type='json', auth='user', website=True)
    def worktop_configurator_get_pricelist(self):
        # On force la société du site web pour obtenir la liste de prix
        pricelist_obj = request.env['product.pricelist']
        return pricelist_obj._get_partner_pricelist(
            partner_id=request.env['res.partner'].browse(request.session['vendor_address_id']).commercial_partner_id.id,
            company_id=request.website.company_id.id)

    @http.route(['/worktop_configurator/compute_price'], type='json', auth='user', website=True)
    def worktop_configurator_compute_price(self, base_price_id, length, width, material_id):
        base_price = request.env['of.worktop.configurator.price'].browse(base_price_id)
        material = request.env['of.worktop.configurator.material'].browse(material_id)
        compute_price = self._compute_product_price(base_price, length, width, material)

        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        product_type = request.env['of.worktop.configurator.type'].browse(request.session['product_type_id'])
        taxes = product_type.product_id.sudo().taxes_id.filtered(lambda r: r.company_id == request.website.company_id)
        tax_id = quote.fiscal_position_id.map_tax(taxes, product_type.product_id, quote.partner_id)

        price = compute_price * self._get_coef()
        total_price = tax_id.compute_all(price, quote.currency_id, 1.0)['total_included']

        return {'price': price, 'total_price': total_price}

    @http.route(['/worktop_configurator/edit_online/<int:quote_id>'], type='http', auth='user', website=True)
    def worktop_configurator_edit_online(self, quote_id, **kw):
        values = kw
        quote = request.env['sale.order'].browse(quote_id)

        # On vide les variables de session
        self._empty_session()

        # On remplit les variables de session
        request.session['worktop_quote_id'] = quote.id
        request.session['customer_address_id'] = quote.partner_shipping_id.id
        request.session['different_invoicing_address'] = \
            'yes' if quote.partner_invoice_id.id != quote.partner_shipping_id.id else 'no'

        vendor = quote.partner_id
        request.session['vendor_address_id'] = vendor.id
        top_vendor = vendor.parent_id if vendor.parent_id else vendor

        if quote.partner_invoice_id in top_vendor.child_ids:
            request.session['invoicing_recipient'] = 'vendor'
            request.session['vendor_invoicing_address_id'] = quote.partner_invoice_id.id
        else:
            request.session['invoicing_recipient'] = 'customer'
            request.session['customer_invoicing_address_id'] = quote.partner_invoice_id.id

        if 'debug' in values:
            return request.redirect('/worktop_configurator/quote_summary?debug=1')
        else:
            return request.redirect('/worktop_configurator/quote_summary')

    @http.route(['/worktop_configurator/edit_line'], type='http', auth='user', website=True)
    def worktop_configurator_edit_line(self, **kw):
        values = kw
        quote_line = request.env['sale.order.line'].browse(int(values['quote_line_id']))

        request.session['worktop_quote_line_id'] = quote_line.id
        request.session['product_type_id'] = quote_line.of_worktop_configurator_type_id.id
        request.session['material_id'] = quote_line.of_worktop_configurator_material_id.id
        request.session['finishing_id'] = quote_line.of_worktop_configurator_finishing_id.id
        request.session['color_id'] = quote_line.of_worktop_configurator_color_id.id
        request.session['thickness_id'] = quote_line.of_worktop_configurator_thickness_id.id
        request.session['length'] = quote_line.of_worktop_configurator_length
        request.session['width'] = quote_line.of_worktop_configurator_width
        request.session['product_price'] = quote_line.price_subtotal
        return request.redirect('/worktop_configurator/product_details')

    @http.route(['/worktop_configurator/duplicate_quote'], type='http', auth='user', website=True)
    def worktop_configurator_duplicate_quote(self, **kw):
        values = kw
        quote = request.env['sale.order'].sudo().browse(int(values['quote_id']))
        quote_copy = quote.copy()
        # On conserve la référence client dans le nouveau devis (champ défini en copy=False)
        quote_copy.client_order_ref = quote.client_order_ref

        return request.redirect('/worktop_configurator/edit_online/%s' % quote_copy.id)

    def _empty_session(self):
        request.session.pop('vendor_address_id', None)
        request.session.pop('customer_address_id', None)
        request.session.pop('invoicing_recipient', None)
        request.session.pop('different_invoicing_address', None)
        request.session.pop('customer_invoicing_address_id', None)
        request.session.pop('vendor_invoicing_address_id', None)
        request.session.pop('worktop_quote_id', None)
        request.session.pop('product_type_id', None)
        request.session.pop('product_price', None)
        request.session.pop('worktop_quote_line_id', None)
        request.session.pop('material_id', None)
        request.session.pop('finishing_id', None)
        request.session.pop('color_id', None)
        request.session.pop('thickness_id', None)
        request.session.pop('length', None)
        request.session.pop('width', None)

    def _create_customer_address(self):
        partner_obj = request.env['res.partner'].sudo()
        params = request.params
        vals = {
            'type': 'contact',
            'name': params.get('name'),
            'email': params.get('email'),
            'phone': params.get('phone'),
            'street': params.get('street'),
            'street2': params.get('street2'),
            'zip': params.get('zip'),
            'city': params.get('city'),
            'country_id': params.get('country_id') and int(params['country_id']),
        }
        partner = partner_obj.create(vals)
        return partner.id

    def _update_customer_address(self, address_id):
        params = request.params
        vals = {}
        address = request.env['res.partner'].sudo().browse(address_id)
        if params.get('name') and params['name'] != address.name:
            vals['name'] = params['name']
        if params.get('phone') != (address.phone or ''):
            vals['phone'] = params.get('phone')
        if params.get('email') != (address.email or ''):
            vals['email'] = params.get('email')
        if params.get('street') and params['street'] != address.street:
            vals['street'] = params['street']
        if params.get('street2') != (address.street2 or ''):
            vals['street2'] = params.get('street2')
        if params.get('zip') and params['zip'] != address.zip:
            vals['zip'] = params['zip']
        if params.get('city') and params['city'] != address.city:
            vals['city'] = params['city']
        if params.get('country_id') and int(params['country_id']) != address.country_id.id:
            vals['country_id'] = int(params['country_id'])
        if vals:
            if request.env['sale.order'].sudo().search_count(
                    [('partner_shipping_id', '=', request.session.get('customer_address_id'))]) <= 1:
                address.write(vals)
                return False
            else:
                return True
        return False

    def _create_invoicing_address(self, parent_id):
        partner_obj = request.env['res.partner'].sudo()
        params = request.params
        vals = {
            'parent_id': parent_id,
            'type': 'invoice',
            'name': params.get('invoicing_name'),
            'email': params.get('invoicing_email'),
            'phone': params.get('invoicing_phone'),
            'street': params.get('invoicing_street'),
            'street2': params.get('invoicing_street2'),
            'zip': params.get('invoicing_zip'),
            'city': params.get('invoicing_city'),
            'country_id': params.get('invoicing_country_id') and int(params['invoicing_country_id']),
        }
        partner = partner_obj.create(vals)
        return partner.id

    def _update_invoicing_address(self, address_id, vendor=False):
        params = request.params
        vals = {}
        address = request.env['res.partner'].sudo().browse(address_id)

        # Cas d'une modification de l'adresse de chantier qui provoque la création d'un nouveau contact
        # On doit donc recréer une nouvelle adresse de facturation rattachée au nouveau contact livraison
        if not vendor and address.parent_id.id != request.session['customer_address_id']:
            return True

        if params.get('invoicing_name') != (address.name or ''):
            vals['name'] = params.get('invoicing_name')
        if params.get('invoicing_phone') != (address.phone or ''):
            vals['phone'] = params.get('invoicing_phone')
        if params.get('invoicing_email') != (address.email or ''):
            vals['email'] = params.get('invoicing_email')
        if params.get('invoicing_street') and params['invoicing_street'] != address.street:
            vals['street'] = params['invoicing_street']
        if params.get('invoicing_street2') != (address.street2 or ''):
            vals['street2'] = params.get('invoicing_street2')
        if params.get('invoicing_zip') and params['invoicing_zip'] != address.zip:
            vals['zip'] = params['invoicing_zip']
        if params.get('invoicing_city') and params['invoicing_city'] != address.city:
            vals['city'] = params['invoicing_city']
        if params.get('invoicing_country_id') and int(params['invoicing_country_id']) != address.country_id.id:
            vals['country_id'] = int(params['invoicing_country_id'])
        if vals:
            if vendor or request.env['sale.order'].sudo().search_count(
                    [('partner_invoice_id', '=', request.session.get('customer_invoicing_address_id'))]) <= 1:
                address.write(vals)
                return False
            else:
                return True
        return False

    def _create_quote(self):
        sale_order_obj = request.env['sale.order'].sudo()
        params = request.params

        # Adresse de livraison
        vendor_address_id = request.session.get('vendor_address_id')
        invoicing_address_id = request.session.get('vendor_invoicing_address_id')
        if request.session.get('invoicing_recipient') == 'customer' or \
                not request.env.user.has_group('base.group_user'):
            if request.session.get('different_invoicing_address') == 'yes':
                invoicing_address_id = request.session.get('customer_invoicing_address_id')
            else:
                invoicing_address_id = request.session.get('customer_address_id')

        # Entrepôt
        warehouse = request.env['stock.warehouse'].sudo().search(
            [('company_id', '=', request.website.company_id.id)], limit=1)

        # Liste de prix
        # On force la société du site web pour obtenir la liste de prix
        pricelist_obj = request.env['product.pricelist']
        pricelist_id = pricelist_obj._get_partner_pricelist(
            partner_id=request.env['res.partner'].browse(vendor_address_id).commercial_partner_id.id,
            company_id=request.website.company_id.id)
        pricelist = pricelist_obj.browse(pricelist_id)

        # Prestation
        service = request.env['of.worktop.configurator.service'].sudo().browse(
            params.get('site_service_id') and int(params['site_service_id']))

        # Condition de règlement
        if service.payment_term_id:
            payment_term_id = service.payment_term_id.id
        else:
            payment_term_id = request.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_payment_term_id')

        # Vendeur
        related_user = request.env['res.users'].sudo().search(
            [('partner_id', '=', vendor_address_id)])
        if not related_user:
            related_user = request.env.user

        vals = {
            'partner_id': vendor_address_id,
            'partner_invoice_id': invoicing_address_id,
            'partner_shipping_id': request.session.get('customer_address_id'),
            'of_worktop_configurator_order': True,
            'fiscal_position_id': params.get('fiscal_pos_id') and int(params['fiscal_pos_id']),
            'company_id': request.website.company_id.id,
            'warehouse_id': warehouse.id,
            'pricelist_id': pricelist.id,
            'user_id': related_user.id,
            'of_worktop_configurator_internal_vendor': request.env.user.has_group('base.group_user'),
            'client_order_ref': params.get('ref'),
            'of_date_de_pose': params.get('delivery_expected_date'),
            'of_delivery_floor': params.get('delivery_floor') and params['delivery_floor'] == 'yes' or False,
            'of_site_service_id': service.id,
            'note2': service.comment_template2_id.get_value(
                vendor_address_id).encode('utf-8') if service.comment_template2_id else False,
            'payment_term_id': payment_term_id,
            'of_junction': params.get('junction') and params['junction'] == 'yes' or False,
        }
        quote = sale_order_obj.create(vals)

        # Création des lignes pour les articles suppléments
        extra_layout_category_id = request.env['ir.values'].sudo().get_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_layout_category_id')

        if quote.of_delivery_floor:
            extra_floor_product_id = request.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_extra_floor_product_id')
            if extra_floor_product_id:
                vals = quote._website_product_id_change(quote.id, extra_floor_product_id, qty=1)
                vals['name'] = quote._get_line_description(quote.id, extra_floor_product_id)
                vals['layout_category_id'] = extra_layout_category_id
                quote_line = request.env['sale.order.line'].sudo().create(vals)
                quote_line.of_no_coef_price = quote_line.price_unit
                quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
                quote_line._compute_tax_id()

        extra_service_product_id = request.env['ir.values'].sudo().get_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_service_product_id')
        if extra_service_product_id:
            vals = quote._website_product_id_change(quote.id, extra_service_product_id, qty=1)
            vals['price_unit'] = quote.of_site_service_id.price
            vals['name'] = quote._get_line_description(quote.id, extra_service_product_id)
            vals['name'] += u"\n%s" % quote.of_site_service_id.name
            vals['layout_category_id'] = extra_layout_category_id
            quote_line = request.env['sale.order.line'].sudo().create(vals)
            quote_line.of_no_coef_price = quote_line.price_unit
            quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
            quote_line._compute_tax_id()

        if quote.of_junction:
            extra_junction_product_id = request.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_extra_junction_product_id')
            if extra_junction_product_id:
                vals = quote._website_product_id_change(quote.id, extra_junction_product_id, qty=1)
                vals['name'] = quote._get_line_description(quote.id, extra_junction_product_id)
                vals['layout_category_id'] = extra_layout_category_id
                quote_line = request.env['sale.order.line'].sudo().create(vals)
                quote_line.of_no_coef_price = quote_line.price_unit
                quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
                quote_line._compute_tax_id()

        return quote.id

    def _update_quote(self, quote_id):
        params = request.params
        vals = {}
        quote = request.env['sale.order'].sudo().browse(quote_id)
        delivery_floor = params.get('delivery_floor') and params['delivery_floor'] == 'yes' or False
        service = request.env['of.worktop.configurator.service'].sudo().browse(
            params.get('site_service_id') and int(params['site_service_id']))
        junction = params.get('junction') and params['junction'] == 'yes' or False
        extra_layout_category_id = request.env['ir.values'].sudo().get_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_layout_category_id')

        if params.get('fiscal_pos_id') and int(params['fiscal_pos_id']) != quote.fiscal_position_id.id:
            vals['fiscal_position_id'] = int(params['fiscal_pos_id'])
        if params.get('ref') != quote.client_order_ref:
            vals['client_order_ref'] = params.get('ref')
        if params.get('delivery_expected_date') != quote.of_date_de_pose:
            vals['of_date_de_pose'] = params.get('delivery_expected_date')
        if delivery_floor != quote.of_delivery_floor:
            vals['of_delivery_floor'] = delivery_floor
            extra_floor_product_id = request.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_extra_floor_product_id')
            if not quote.of_delivery_floor and extra_floor_product_id:
                line_vals = quote._website_product_id_change(quote.id, extra_floor_product_id, qty=1)
                line_vals['name'] = quote._get_line_description(quote.id, extra_floor_product_id)
                line_vals['layout_category_id'] = extra_layout_category_id
                quote_line = request.env['sale.order.line'].sudo().create(line_vals)
                quote_line.of_no_coef_price = quote_line.price_unit
                quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
                quote_line._compute_tax_id()
            elif not delivery_floor and extra_floor_product_id:
                quote.order_line.filtered(lambda l: l.product_id.id == extra_floor_product_id).unlink()
        if service != quote.of_site_service_id:
            vals['of_site_service_id'] = service.id
            extra_service_product_id = request.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_extra_service_product_id')
            if extra_service_product_id:
                quote_line = quote.order_line.filtered(lambda l: l.product_id.id == extra_service_product_id)
                quote_line.of_no_coef_price = service.price
                quote_line.price_unit = service.price * quote_line.get_pricelist_coef()
                quote_line.name = quote._get_line_description(quote.id, extra_service_product_id)
                quote_line.name += u"\n%s" % service.name
                quote_line._compute_tax_id()
            if service.payment_term_id:
                vals['payment_term_id'] = service.payment_term_id.id
            else:
                vals['payment_term_id'] = request.env['ir.values'].sudo().get_default(
                    'sale.config.settings', 'of_website_worktop_configurator_payment_term_id')
            vals['note2'] = service.comment_template2_id.get_value(quote.partner_id.id).encode('utf-8') \
                if service.comment_template2_id else False
        if junction != quote.of_junction:
            vals['of_junction'] = junction
            extra_junction_product_id = request.env['ir.values'].sudo().get_default(
                'sale.config.settings', 'of_website_worktop_configurator_extra_junction_product_id')
            if junction and extra_junction_product_id:
                line_vals = quote._website_product_id_change(quote.id, extra_junction_product_id, qty=1)
                line_vals['name'] = quote._get_line_description(quote.id, extra_junction_product_id)
                line_vals['layout_category_id'] = extra_layout_category_id
                quote_line = request.env['sale.order.line'].sudo().create(line_vals)
                quote_line.of_no_coef_price = quote_line.price_unit
                quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
                quote_line._compute_tax_id()
            elif extra_junction_product_id:
                quote.order_line.filtered(lambda l: l.product_id.id == extra_junction_product_id).unlink()

        if vals:
            quote.write(vals)
            self._compute_discount()

    def _get_product_price(self):
        params = request.params

        # On force la société du site web pour obtenir la liste de prix
        pricelist_obj = request.env['product.pricelist']
        pricelist_id = pricelist_obj._get_partner_pricelist(
            partner_id=request.env['res.partner'].browse(request.session['vendor_address_id']).commercial_partner_id.id,
            company_id=request.website.company_id.id)
        pricelist = pricelist_obj.browse(pricelist_id)

        config_price = request.env['of.worktop.configurator.price'].search(
            [('material_id', '=', int(params['material_id'])),
             ('finishing_id', '=', int(params['finishing_id'])),
             ('color_ids', 'in', int(params['color_id'])),
             ('pricelist_ids', 'in', pricelist.id or False),
             ('thickness_id', '=', int(params['thickness_id']))], limit=1)
        length = round(float(params['length'].replace(',', '.')), 2)
        width = round(float(params['width'].replace(',', '.')), 2)
        material = request.env['of.worktop.configurator.material'].browse(int(params['material_id']))
        return self._compute_product_price(config_price, length, width, material)

    def _compute_product_price(self, base_price, length, width, material):
        if base_price:
            if width < 55.0 or width >= 69.0:
                price = base_price.price * (width * 1.1 / 60.0) * (length / 100.0)
            else:
                price = base_price.price * (length / 100.0)
            # Cut to size
            surface = (length / 100.0) * (width / 100.0)
            if surface < 2.0:
                price *= material.cut_to_size_coeff
            return price
        else:
            return 0.0

    def _get_coef(self):
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        product_type = request.env['of.worktop.configurator.type'].browse(request.session['product_type_id']).sudo()
        items = quote.pricelist_id.item_ids.filtered(
            lambda i: i.applied_on == '0_product_variant' and i.product_id.id == product_type.product_id.id and
            i.compute_price == 'coef')
        if not items:
            items = quote.pricelist_id.item_ids.filtered(
                lambda i: i.applied_on == '1_product' and
                i.product_tmpl_id.id == product_type.product_id.product_tmpl_id.id and i.compute_price == 'coef')
        if not items:
            items = quote.pricelist_id.item_ids.filtered(
                lambda i: i.applied_on == '2_product_category' and i.categ_id.id == product_type.product_id.categ_id.id
                and i.compute_price == 'coef')
        if not items:
            items = quote.pricelist_id.item_ids.filtered(
                lambda i: i.applied_on == '2.5_brand' and i.of_brand_id.id == product_type.product_id.brand_id.id and
                i.compute_price == 'coef')
        if not items:
            items = quote.pricelist_id.item_ids.filtered(
                lambda i: i.applied_on == '3_global' and i.compute_price == 'coef')
        return items and items[0].of_coef or 1.0

    def _create_quote_line(self):
        params = request.params
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        product_type = request.env['of.worktop.configurator.type'].browse(request.session['product_type_id'])

        length = round(float(params['length'].replace(',', '.')), 2)
        width = round(float(params['width'].replace(',', '.')), 2)

        request.session['material_id'] = int(params['material_id'])
        material = request.env['of.worktop.configurator.material'].browse(int(params['material_id']))
        request.session['finishing_id'] = int(params['finishing_id'])
        finishing = request.env['of.worktop.configurator.finishing'].browse(int(params['finishing_id']))
        request.session['color_id'] = int(params['color_id'])
        color = request.env['of.worktop.configurator.color'].browse(int(params['color_id']))
        request.session['thickness_id'] = int(params['thickness_id'])
        thickness = request.env['of.worktop.configurator.thickness'].browse(int(params['thickness_id']))
        request.session['length'] = length
        request.session['width'] = width

        vals = quote._website_product_id_change(quote.id, product_type.product_id.id, qty=1)
        vals['layout_category_id'] = product_type.layout_category_id.id
        request.session['product_price'] = self._get_product_price()
        vals['price_unit'] = request.session['product_price']
        vals['name'] = quote._get_line_description(quote.id, product_type.product_id.id)
        vals['name'] += u"\nMatériau : %s" % material.name
        vals['name'] += u"\nFinition : %s" % finishing.name
        vals['name'] += u"\nCouleur : %s" % color.name
        vals['name'] += u"\nLongueur : %s" % length
        vals['name'] += u"\nLargeur : %s" % width
        vals['name'] += u"\nÉpaisseur & type de chant : %s" % thickness.name
        vals['of_worktop_configurator_type_id'] = product_type.id
        vals['of_worktop_configurator_material_id'] = material.id
        vals['of_worktop_configurator_finishing_id'] = finishing.id
        vals['of_worktop_configurator_color_id'] = color.id
        vals['of_worktop_configurator_thickness_id'] = thickness.id
        vals['of_worktop_configurator_length'] = length
        vals['of_worktop_configurator_width'] = width
        # Weight
        weight = length * width * thickness.value * material.unit_weight
        vals['of_worktop_configurator_weight'] = weight

        quote_line = request.env['sale.order.line'].sudo().create(vals)
        quote_line.of_no_coef_price = quote_line.price_unit
        quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
        quote_line._compute_tax_id()
        return quote_line.id

    def _update_quote_line(self, quote_line_id):
        params = request.params
        vals = {}
        quote_line = request.env['sale.order.line'].sudo().browse(quote_line_id)
        product_type = request.env['of.worktop.configurator.type'].browse(request.session['product_type_id'])

        length = round(float(params['length'].replace(',', '.')), 2)
        width = round(float(params['width'].replace(',', '.')), 2)

        if int(params['material_id']) != request.session['material_id'] or \
                int(params['finishing_id']) != request.session['finishing_id'] or \
                int(params['color_id']) != request.session['color_id'] or \
                int(params['thickness_id']) != request.session['thickness_id'] or \
                length != request.session['length'] or \
                width != request.session['width']:
            request.session['material_id'] = int(params['material_id'])
            material = request.env['of.worktop.configurator.material'].browse(int(params['material_id']))
            request.session['finishing_id'] = int(params['finishing_id'])
            finishing = request.env['of.worktop.configurator.finishing'].browse(int(params['finishing_id']))
            request.session['color_id'] = int(params['color_id'])
            color = request.env['of.worktop.configurator.color'].browse(int(params['color_id']))
            request.session['thickness_id'] = int(params['thickness_id'])
            thickness = request.env['of.worktop.configurator.thickness'].browse(int(params['thickness_id']))
            request.session['length'] = length
            request.session['width'] = width

            request.session['product_price'] = self._get_product_price()
            vals['price_unit'] = request.session['product_price']
            vals['name'] = quote_line.order_id._get_line_description(quote_line.order_id.id, quote_line.product_id.id)
            vals['name'] += u"\nMatériau : %s" % material.name
            vals['name'] += u"\nFinition : %s" % finishing.name
            vals['name'] += u"\nCouleur : %s" % color.name
            vals['name'] += u"\nLongueur : %s" % length
            vals['name'] += u"\nLargeur : %s" % width
            vals['name'] += u"\nÉpaisseur & type de chant: %s" % thickness.name
            vals['of_worktop_configurator_type_id'] = product_type.id
            vals['of_worktop_configurator_material_id'] = material.id
            vals['of_worktop_configurator_finishing_id'] = finishing.id
            vals['of_worktop_configurator_color_id'] = color.id
            vals['of_worktop_configurator_thickness_id'] = thickness.id
            vals['of_worktop_configurator_length'] = length
            vals['of_worktop_configurator_width'] = width
            # Weight
            weight = length * width * thickness.value * material.unit_weight
            vals['of_worktop_configurator_weight'] = weight

            quote_line.write(vals)
            quote_line.of_no_coef_price = quote_line.price_unit
            quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
            quote_line._compute_tax_id()

    def _control_weight(self):
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        extra_weight_product_id = request.env['ir.values'].sudo().get_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_weight_product_id')
        extra_layout_category_id = request.env['ir.values'].sudo().get_default(
            'sale.config.settings', 'of_website_worktop_configurator_extra_layout_category_id')
        weights = quote.order_line.mapped('of_worktop_configurator_weight')
        max_weight = weights and max(weights) or 0
        if extra_weight_product_id:
            if max_weight >= 150.0 and not quote.order_line.filtered(
                    lambda l: l.product_id.id == extra_weight_product_id):
                # On ajoute le supplément de poids
                vals = quote._website_product_id_change(quote.id, extra_weight_product_id, qty=1)
                vals['name'] = quote._get_line_description(quote.id, extra_weight_product_id)
                vals['layout_category_id'] = extra_layout_category_id
                quote_line = request.env['sale.order.line'].sudo().create(vals)
                quote_line.of_no_coef_price = quote_line.price_unit
                quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
                quote_line._compute_tax_id()
            if max_weight < 150.0 and quote.order_line.filtered(lambda l: l.product_id.id == extra_weight_product_id):
                # On supprime le supplément poids
                quote.order_line.filtered(lambda l: l.product_id.id == extra_weight_product_id).unlink()

    def _compute_discount(self):
        quote = request.env['sale.order'].sudo().browse(request.session['worktop_quote_id'])
        discount_product_id = request.env['ir.values'].sudo().get_default(
            'sale.config.settings', 'of_website_worktop_configurator_discount_product_id')
        if discount_product_id:
            # On supprime la ligne de remise si elle est déjà présente
            quote.order_line.filtered(lambda l: l.product_id.id == discount_product_id).unlink()
            # On traite la nouvelle remise
            if quote.of_worktop_configurator_discount_id:
                # On calcul le prix de la remise
                discount_price = -quote.amount_untaxed * (quote.of_worktop_configurator_discount_id.value / 100.0)
                # On ajoute la ligne de remise
                vals = quote._website_product_id_change(quote.id, discount_product_id, qty=1)
                vals['name'] = quote._get_line_description(quote.id, discount_product_id)
                vals['price_unit'] = discount_price
                quote_line = request.env['sale.order.line'].sudo().create(vals)
                quote_line.of_no_coef_price = quote_line.price_unit
                quote_line.price_unit = quote_line.price_unit * quote_line.get_pricelist_coef()
                quote_line._compute_tax_id()

        # On recalcule l'échéancier
        quote.of_echeance_line_ids = quote._of_compute_echeances()
