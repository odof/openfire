odoo.define('of_point_of_sale.models', function (require) {

    var models = require('point_of_sale.models');

    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        load_server_data: function () {
            var self = this;

            var product_index = _.findIndex(this.models, function (model) {
                return model.model === 'product.product';
            });
            this.models[product_index]['order'] = ['-of_pos_favorite','sequence','default_code','name'];

            return posmodel_super.load_server_data.apply(this, arguments);
        },
    });

});