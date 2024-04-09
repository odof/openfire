# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.attachment_mutation import AttachmentMutation
from ..graphql.attachment_query import AttachmentQuery
from ..graphql.attachment_type import Attachment, AttachmentCreateInput, AttachmentFilterInput, AttachmentUpdateInput
from ..graphql.company_mutation import CompanyMutation
from ..graphql.company_query import CompanyQuery
from ..graphql.company_type import Company, CompanyCreateInput, CompanyFilterInput, CompanyInput, CompanyUpdateInput
from ..graphql.employee_mutation import EmployeeMutation
from ..graphql.employee_query import EmployeeQuery
from ..graphql.employee_type import Employee, EmployeeCreateInput, EmployeeFilterInput, EmployeeUpdateInput
from ..graphql.partner_mutation import PartnerMutation
from ..graphql.partner_phone_mutation import PartnerPhoneMutation
from ..graphql.partner_phone_type import PartnerPhone, PartnerPhoneCreateInput, PartnerPhoneUpdateInput
from ..graphql.partner_query import PartnerQuery
from ..graphql.partner_title_mutation import PartnerTitleMutation
from ..graphql.partner_title_query import PartnerTitleQuery
from ..graphql.partner_title_type import PartnerTitle, PartnerTitleCreateInput, PartnerTitleUpdateInput
from ..graphql.partner_type import Partner, PartnerCreateInput, PartnerFilterInput, PartnerInput, PartnerUpdateInput
from ..graphql.product_category_mutation import ProductCategoryMutation
from ..graphql.product_category_query import ProductCategoryQuery
from ..graphql.product_category_type import ProductCategory, ProductCategoryCreateInput, ProductCategoryUpdateInput
from ..graphql.product_mutation import ProductMutation
from ..graphql.product_query import ProductQuery
from ..graphql.product_template_mutation import ProductTemplateMutation
from ..graphql.product_template_query import ProductTemplateQuery
from ..graphql.product_template_type import (
    ProductTemplate,
    ProductTemplateCreateInput,
    ProductTemplateFilterInput,
    ProductTemplateUpdateInput,
)
from ..graphql.product_type import Product, ProductCreateInput, ProductFilterInput, ProductInput, ProductUpdateInput
from ..graphql.user_type import User

logger = logging.getLogger(__name__)


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_base_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Attachment,
                AttachmentCreateInput,
                AttachmentFilterInput,
                AttachmentUpdateInput,
                AttachmentMutation,
                AttachmentQuery,
                PartnerMutation,
                PartnerQuery,
                PartnerInput,
                PartnerCreateInput,
                PartnerFilterInput,
                Partner,
                PartnerUpdateInput,
                PartnerPhone,
                PartnerPhoneCreateInput,
                PartnerPhoneUpdateInput,
                PartnerPhoneMutation,
                PartnerTitle,
                PartnerTitleCreateInput,
                PartnerTitleUpdateInput,
                PartnerTitleMutation,
                PartnerTitleQuery,
                ProductCategoryQuery,
                ProductCategory,
                ProductCategoryCreateInput,
                ProductCategoryUpdateInput,
                ProductCategoryMutation,
                ProductQuery,
                Product,
                ProductMutation,
                ProductInput,
                ProductCreateInput,
                ProductFilterInput,
                ProductUpdateInput,
                ProductTemplateQuery,
                ProductTemplate,
                ProductTemplateMutation,
                ProductTemplateCreateInput,
                ProductTemplateFilterInput,
                ProductTemplateUpdateInput,
                Employee,
                EmployeeFilterInput,
                EmployeeQuery,
                Company,
                CompanyMutation,
                CompanyQuery,
                CompanyInput,
                CompanyCreateInput,
                CompanyUpdateInput,
                CompanyFilterInput,
                EmployeeMutation,
                EmployeeCreateInput,
                EmployeeUpdateInput,
                User,
            ],
        )
