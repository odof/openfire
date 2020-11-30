odoo.define('of_pos_multicompany.models', function (require) {

    var models = require('point_of_sale.models');

    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        load_server_data: function () {
            var self = this;

            var company_index = _.findIndex(this.models, function (model) {
                return model.model === 'res.company';
            });
            this.models[company_index]['fields'].push('accounting_company_id');

            var tax_index = _.findIndex(this.models, function (model) {
                return model.model === 'account.tax';
            });
            this.models[tax_index]['domain'] = function(self) {
                return [['company_id', '=', self.company && self.company.accounting_company_id && self.company.accounting_company_id[0] || false]]
            };

            return posmodel_super.load_server_data.apply(this, arguments);
        },
    });

});