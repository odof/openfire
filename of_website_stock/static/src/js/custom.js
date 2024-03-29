odoo.define('of_website_stock.of_website_stock_notify', function(require) {
    "use strict";
    var core = require('web.core');
    var _t = core._t;
    var ajax = require('web.ajax');

    $(document).ready(function() {

        var $form_data = $('div.js_product').closest('form');
        var $js_qty = $form_data.find('.css_quantity.input-group.oe_website_spinner');

        var $stock_qty_message = $('div.out-of-stock');
        if($stock_qty_message.length === 1){
            $('#add_to_cart').hide();
            $js_qty.hide();
        } else {
            $('#add_to_cart').show();
            $js_qty.show();
        }

        $('.oe_website_sale').each(function () {
            var oe_website_sale = this;
            
            show_hide_stock_change();
            $(oe_website_sale).on('change', function(ev) {
                show_hide_stock_change();
            });

            function show_hide_stock_change() {
                var $product_details = $('#product_details');
                var $form_data = $('div.js_product').closest('form');
                var $js_qty = $form_data.find('.css_quantity.input-group.oe_website_spinner');

                if ($("input[name='product_id']").is(':radio')){
                    var product_id = $form_data.find("input[name='product_id']:checked").val();
                } else {
                    var product_id = $form_data.find("input[name='product_id']").val();

                    var qty_available = $product_details.find('#' + product_id).attr('value');
                    var $form_notify = $product_details.find('.js_notify_email').closest('form');
                    var notify = $form_notify.find("input[name='notify']").val();
                    $product_details.find('.show_hide_stock_change').hide();
                    $product_details.find('#' + product_id).show();
                    if (qty_available <= 0 && parseInt(notify)) {
                        $('#add_to_cart').hide();
                        $js_qty.hide();
                        $form_notify.show();
                    } else {
                        $('#add_to_cart').show();
                        $js_qty.show();
                        $form_notify.hide();
                    }
                }
            }

            $(oe_website_sale).on("change", 'input[name="add_qty"]', function (event) {
                var product_ids = [];
                var $product_details = $('#product_details');
                var $target = $(event.target);
                var $target_input_group = $target.closest('.input-group');
                var qty = $target.val();

                if ($("input[name='product_id']").is(':radio')){
                    var product_id = $form_data.find("input[name='product_id']:checked").val();
                } else {
                    var product_id = $form_data.find("input[name='product_id']").val();

                    var qty_available = $product_details.find('#' + product_id).attr('value');
                    var $form_notify = $product_details.find('#' + product_id).find('.js_notify_email').closest('form');
                    var notify = $form_notify.find("input[name='notify']").val();
                    if (qty_available < parseFloat(qty || 0) && parseInt(notify)) {
                        $('#add_to_cart').hide();
                        $form_notify.show();

                        var qty = $(event.target).closest('form').find('input[name="add_qty"]').val(parseInt(qty_available));

                        $target.popover({
                            animation: true,
                            title: _t('DENIED'),
                            container: $target_input_group,
                            placement: 'bottom',
                            content: _t('You Can Not Add More than Available Quantity'),
                        });
                        $target.popover('show');
                        setTimeout(function() {
                            $target.popover('hide');
                            $target.popover('destroy');
                        }, 2500);
                    } else {
                        $('#add_to_cart').show();
                        $target.show();
                        $form_notify.hide();
                    }
                }
            });

            $(oe_website_sale).on("change", '.oe_cart input.js_quantity[data-product-id]', function (event) {
                var $input_product_id = $(this);
                var qty = $input_product_id.val();
                var qty_available = parseInt($(this).data('qty'),10);

                if (qty_available < qty) {
                    $input_product_id.val(qty_available);
                    $input_product_id.popover({
                        animation: true,
                        title: _t('DENIED'),
                        container: 'body',
                        placement: 'top',
                        html: true,
                        content: _t('You Can Not Add More than Available Quantity'),
                    });
                    $input_product_id.popover('show');
                    setTimeout(function() {
                        $input_product_id.popover('hide');
                        $input_product_id.popover('destroy');
                    }, 2500);
                }
            });

            $(oe_website_sale).on("click", ".js_notify_btn", function() {
                var self = this;
                var $form_data = $(this).closest('form');
                var $data = $form_data.find('.js_notify').first();;
                var $product = $data.attr('id');
                var $email =$form_data.find('.js_notify_email').val();

                if ($email.length == 0  || !$email.match(/^([\w-\.]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([\w-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?)$/)) {
                    $form_data.addClass('has-error');
                    $form_data.find(".danger-message").removeClass("hidden");
                    return false;
                }
                $form_data.removeClass('has-error');
                $form_data.find(".danger-message").addClass("hidden");

                ajax.jsonRpc('/website_sale_stock_notify/notify', 'call', {
                    'product_id': $product,
                    'email': $email,
                }).then(function (notify) {
                    $data.find(".js_notify_email, .input-group-btn").addClass("hidden");
                    $data.find(".success-message").removeClass("hidden");
                });
            });
        });
    });
});;
