# -*- coding: utf-8 -*-

from odoo import api, models
from lxml.etree import Element, SubElement, QName, tounicode, tostring
from odoo.addons.website.models.website import slug


class XMLNamespaces:
    g = 'http://base.google.com/ns/1.0'


class OfGoogleShopping(models.TransientModel):
    _name = 'of.google.shopping'

    def create_xml_file(self):
        website_id = self.env['website'].search([], limit=1)
        product_ids = self.env['product.template'].search(
            [('website_published', '=', True), ('type', 'in', ['consu', 'product'])])

        rss = Element('rss', nsmap={'g': XMLNamespaces.g})
        rss.set("version", "2.0")

        channel = SubElement(rss, "channel")

        title = SubElement(channel, "title")
        link = SubElement(channel, "link")
        description = SubElement(channel, "description")

        title.text = website_id.name
        link.text = website_id.domain
        description.text = "XML file for Google Shopping"

        for product in product_ids:
            self.create_item(website_id, channel, product)

        return tostring(rss, pretty_print=True, xml_declaration=True, encoding='utf-8')

    def create_item(self, website_id, channel, product):
        # S'il manque un champ obligatoire, on ignore l'article
        if (product.description_sale or product.description_sale) and product.list_price:

            item = SubElement(channel, "item")

            # Obligatoire
            id = SubElement(channel, QName(XMLNamespaces.g, 'id'))
            title = SubElement(channel, QName(XMLNamespaces.g, 'title'))
            description = SubElement(channel, QName(XMLNamespaces.g, 'description'))
            link = SubElement(channel, QName(XMLNamespaces.g, 'link'))
            image_link = SubElement(channel, QName(XMLNamespaces.g, 'image_link'))
            condition = SubElement(channel, QName(XMLNamespaces.g, 'condition'))
            availability = SubElement(channel, QName(XMLNamespaces.g, 'availability'))
            price = SubElement(channel, QName(XMLNamespaces.g, 'price'))

            id.text = str(product.id)
            title.text = product.name[0:150]
            if product.website_description:
                description.text = product.website_description[0:5000]
            else:
                description.text = product.description_sale[0:5000]
            link.text = '%s/shop/product/%s' % (website_id.domain, slug(product))
            image_link.text = '%s/web/image/product.template/%s/image' % (website_id.domain, product.id)
            condition.text = 'new'
            availability.text = 'in_stock'
            price.text = '%s EUR' % str(product.list_price)

            # Obligatoire pour tous les produits neufs auxquels un code GTIN a été attribué par le fabricant
            if product.barcode:
                gtin = SubElement(channel, QName(XMLNamespaces.g, 'gtin'))
                gtin.text = product.barcode[0:70]

            # Facultatif
            if product.brand_id:
                brand = SubElement(channel, QName(XMLNamespaces.g, 'brand'))
                brand.text = product.brand_id.name[0:70]
            if product.public_categ_ids:
                product_type = SubElement(channel, QName(XMLNamespaces.g, 'product_type'))
                product_type.text = unicode(product.public_categ_ids[0].name_get()[0][1])[0:750]

            condition = SubElement(channel, QName(XMLNamespaces.g, 'condition'))
            condition.text = 'new'
            adult = SubElement(channel, QName(XMLNamespaces.g, 'adult'))
            adult.text = 'no'
