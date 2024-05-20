# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.attachment_mutation import AttachmentMutation
from ..graphql.attachment_query import AttachmentQuery
from ..graphql.attachment_type import Attachment, AttachmentFilterInput
from ..graphql.company_mutation import CompanyMutation
from ..graphql.company_query import CompanyQuery
from ..graphql.company_type import CompanyFilterInput, CompanyInput
from ..graphql.employee_mutation import EmployeeMutation
from ..graphql.employee_query import EmployeeQuery
from ..graphql.employee_type import Employee, EmployeeFilterInput
from ..graphql.image_mutation import ImageMutation
from ..graphql.image_query import ImageQuery
from ..graphql.image_type import Image, ImageFilterInput
from ..graphql.partner_mutation import PartnerMutation
from ..graphql.partner_phone_mutation import PartnerPhoneMutation
from ..graphql.partner_phone_type import PartnerPhone
from ..graphql.partner_query import PartnerQuery
from ..graphql.partner_title_mutation import PartnerTitleMutation
from ..graphql.partner_title_query import PartnerTitleQuery
from ..graphql.partner_title_type import PartnerTitle
from ..graphql.partner_type import Partner, PartnerFilterInput, PartnerInput
from ..graphql.product_category_mutation import ProductCategoryMutation
from ..graphql.product_category_query import ProductCategoryQuery
from ..graphql.product_category_type import ProductCategory
from ..graphql.product_mutation import ProductMutation
from ..graphql.product_query import ProductQuery
from ..graphql.product_template_mutation import ProductTemplateMutation
from ..graphql.product_template_query import ProductTemplateQuery
from ..graphql.product_template_type import ProductTemplate, ProductTemplateFilterInput
from ..graphql.product_type import Product, ProductFilterInput, ProductInput
from ..graphql.user_type import User, UserInput

logger = logging.getLogger(__name__)


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_base_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Attachment,
                AttachmentFilterInput,
                AttachmentMutation,
                AttachmentQuery,
                PartnerMutation,
                PartnerQuery,
                PartnerInput,
                PartnerFilterInput,
                Partner,
                PartnerPhone,
                PartnerPhoneMutation,
                PartnerTitle,
                PartnerTitleMutation,
                PartnerTitleQuery,
                ProductCategoryQuery,
                ProductCategory,
                ProductCategoryMutation,
                ProductQuery,
                Product,
                ProductMutation,
                ProductInput,
                ProductFilterInput,
                ProductTemplateQuery,
                ProductTemplate,
                ProductTemplateMutation,
                ProductTemplateFilterInput,
                Image,
                ImageFilterInput,
                ImageQuery,
                ImageMutation,
                Employee,
                EmployeeFilterInput,
                EmployeeQuery,
                CompanyMutation,
                CompanyQuery,
                CompanyInput,
                CompanyFilterInput,
                EmployeeMutation,
                User,
                UserInput,
            ],
        )
