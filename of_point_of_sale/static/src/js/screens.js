odoo.define('of_point_of_sale.screens', function (require) {

    var screens = require('point_of_sale.screens');
    var PaymentScreenWidget = screens.PaymentScreenWidget;
    var Model = require('web.DataModel');
    var Partners = new Model('res.partner');
    var Values = new Model('ir.values');

    PaymentScreenWidget.include({
        click_invoice: function(){
            var order = this.pos.get_order();
            order.set_to_invoice(!order.is_to_invoice());
            if (order.is_to_invoice()) {
                this.$('.js_invoice').addClass('highlight');
                if (!order.get_client()) {
                    Values.query(['id', 'name', 'value_unpickle'])
                        .filter([['name', '=', 'default_invoice_customer_id'], ['model', '=', 'pos.config.settings']])
                        .limit(1)
                        .all()
                        .then(function (client_id) {
                            Partners.query(['id', 'name'])
                                .filter([['active', '=', true], ['id', '=', client_id[0].value_unpickle]])
                                .limit(1)
                                .all()
                                .then(function (user) {
                                    order.set_client(user[0]);
                            });
                    });
                }
            } else {
                this.$('.js_invoice').removeClass('highlight');
            }
        },
    });
});
