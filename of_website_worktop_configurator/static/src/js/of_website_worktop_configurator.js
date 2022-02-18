odoo.define('of_website_worktop_configurator.worktop_configurator', function (require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var utils = require('web.utils');
    var core = require('web.core');
    var config = require('web.config');
    var Model = require("web.Model");
    var _t = core._t;

    if(!$('.oe_of_website_worktop_configurator').length) {
        return $.Deferred().reject("DOM doesn't contain '.oe_of_website_worktop_configurator'");
    }

    $('.oe_of_website_worktop_configurator').each(function () {
        var oe_of_website_worktop_configurator = this;

        var clickwatch = (function(){
            var timer = 0;
            return function(callback, ms){
                clearTimeout(timer);
                timer = setTimeout(callback, ms);
            };
        })();


        // Bouton loading
        $('.oe_of_website_worktop_configurator .a-submit, #comment .a-submit').off('click').on('click', function (event) {
            if (!event.isDefaultPrevented() && !$(this).is(".disabled")) {
                $(this).closest('form').submit();
            }
            if ($(this).hasClass('a-submit-disable')){
                $(this).addClass("disabled");
            }
            if ($(this).hasClass('a-submit-loading')){
                var loading = '<span class="fa fa-cog fa-spin"/>';
                var fa_span = $(this).find('span[class*="fa"]');
                if (fa_span.length){
                    fa_span.replaceWith(loading);
                }
                else{
                    $(this).append(loading);
                }
            }
        });

        // Adresses //

        if ($(".address_autoformat").length) {
            $(oe_of_website_worktop_configurator).on('change', "select[name='country_id']", function () {
                clickwatch(function() {
                    if ($("#country_id").val()) {
                        ajax.jsonRpc("/shop/country_infos/" + $("#country_id").val(), 'call', {mode: 'shipping'}).then(
                            function(data) {
                                // manage fields order / visibility
                                if (data.fields) {
                                    if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)){
                                        $(".div_zip").before($(".div_city"));
                                    }
                                    else {
                                        $(".div_zip").after($(".div_city"));
                                    }
                                    var all_fields = ["street", "zip", "city", "country_name"];
                                    _.each(all_fields, function(field) {
                                        $(".address_autoformat .div_" + field.split('_')[0]).toggle($.inArray(field, data.fields)>=0);
                                    });
                                }
                            }
                        );
                    }
                }, 500);
            });
            $(oe_of_website_worktop_configurator).on('change', "select[name='invoicing_country_id']", function () {
                clickwatch(function() {
                    if ($("#invoicing_country_id").val()) {
                        ajax.jsonRpc("/shop/country_infos/" + $("#invoicing_country_id").val(), 'call', {mode: 'shipping'}).then(
                            function(data) {
                                // manage fields order / visibility
                                if (data.fields) {
                                    if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)){
                                        $(".div_invoicing_zip").before($(".div_invoicing_city"));
                                    }
                                    else {
                                        $(".div_invoicing_zip").after($(".div_invoicing_city"));
                                    }
                                    var all_fields = ["street", "zip", "city", "country_name"];
                                    _.each(all_fields, function(field) {
                                        $(".address_autoformat .div_invoicing_" + field).toggle($.inArray(field, data.fields)>=0);
                                    });
                                }
                            }
                        );
                    }
                }, 500);
            });
        }
        $("select[name='country_id']").change();
        $("select[name='invoicing_country_id']").change();

        // Visibilité des adresses de facturation
        if ($(".configurator_customer_address").length) {
            $(oe_of_website_worktop_configurator).on('change', "input[type=radio][name=invoicing_recipient]", function () {
                clickwatch(function() {
                    var value = $("input[type=radio][name=invoicing_recipient]:checked").val();
                    if (value == 'vendor') {
                        $(".div_all_vendor_addresses").show();
                        $("input[type=radio][name=different_invoicing_address]:checked").prop('checked', false);
                        $(".div_different_invoicing_address").hide();
                        $(".div_invoicing_address").hide();
                    }
                    else if (value == 'customer') {
                        $(".div_different_invoicing_address").show();
                        $(".div_all_vendor_addresses").hide();

                        $("input[name='invoicing_street']").parent('div').removeClass('has-error');
                        $("input[name='invoicing_zip']").parent('div').removeClass('has-error');
                        $("input[name='invoicing_city']").parent('div').removeClass('has-error');
                        $("input[name='invoicing_country_id']").parent('div').removeClass('has-error');

                        $(".div_invoicing_address").hide();
                        $("input[name='invoicing_name']").val("");
                        $("input[name='invoicing_email']").val("");
                        $("input[name='invoicing_phone']").val("");
                        $("input[name='invoicing_street']").val("");
                        $("input[name='invoicing_street2']").val("");
                        $("input[name='invoicing_zip']").val("");
                        $("input[name='invoicing_city']").val("");

                        $("input[name='create_vendor_address']").val("no");
                        $("input[name='update_vendor_address']").val("no");
                    }
                }, 500);
            });
            $(oe_of_website_worktop_configurator).on('change', "input[type=radio][name=different_invoicing_address]", function () {
                clickwatch(function() {
                    var value = $("input[type=radio][name=different_invoicing_address]:checked").val();
                    if (value == 'no') {
                        $(".div_invoicing_address").hide();
                    }
                    else if (value == 'yes') {
                        $(".div_invoicing_address").show();
                    }
                }, 500);
            });
        }

        // Sélecteur d'adresse kanban
        $('.configurator_customer_address').on('click', '.of_js_change_address', function() {
            if (!$('body.editor_enable').length) { //allow to edit button text with editor
                var $old = $('.div_all_vendor_addresses').find('.panel.of_border_primary');
                $old.find('.btn-ship').toggle();
                $old.addClass('of_js_change_address');
                $old.removeClass('of_border_primary');

                var $new = $(this).parent('div.one_kanban').find('.panel');
                $new.find('.btn-ship').toggle();
                $new.removeClass('of_js_change_address');
                $new.addClass('of_border_primary');

                var address_id = $(this).parent('div.one_kanban').find('#vendor_invoicing_address_id').text();
                $.post('/worktop_configurator/customer_details', 'csrf_token='+odoo.csrf_token+'&vendor_invoicing_address_id='+address_id+'&xhr=1');
            }
        });

        // Modification adresse kanban
        $(oe_of_website_worktop_configurator).on('click', '.of_js_edit_address', function() {
            $(".div_all_vendor_addresses").hide();
            $(".div_invoicing_address").show();

            var address_id = $(this).parent('div.one_kanban').find('#vendor_invoicing_address_id').text();
            ajax.jsonRpc("/worktop_configurator/get_address_field", 'call', {
                'address_id': address_id,
            }).then(function (data) {
                $("input[name='invoicing_street']").parent('div').removeClass('has-error');
                $("input[name='invoicing_zip']").parent('div').removeClass('has-error');
                $("input[name='invoicing_city']").parent('div').removeClass('has-error');
                $("input[name='invoicing_country_id']").parent('div').removeClass('has-error');

                $("input[name='invoicing_name']").val(data['name']);
                $("input[name='invoicing_email']").val(data['email']);
                $("input[name='invoicing_phone']").val(data['phone']);
                $("input[name='invoicing_street']").val(data['street']);
                $("input[name='invoicing_street2']").val(data['street2']);
                $("input[name='invoicing_zip']").val(data['zip']);
                $("input[name='invoicing_city']").val(data['city']);
                $("select[name='invoicing_country_id']").val(data['country_id']);

                $("input[name='create_vendor_address']").val("no");
                $("input[name='update_vendor_address']").val("yes");
            });
        });

        // Ajout adresse
        $(oe_of_website_worktop_configurator).on('click', '.of_js_add_address', function() {
            $(".div_all_vendor_addresses").hide();
            $(".div_invoicing_address").show();

            $("input[name='invoicing_street']").parent('div').removeClass('has-error');
            $("input[name='invoicing_zip']").parent('div').removeClass('has-error');
            $("input[name='invoicing_city']").parent('div').removeClass('has-error');
            $("input[name='invoicing_country_id']").parent('div').removeClass('has-error');

            $("input[name='invoicing_name']").val("");
            $("input[name='invoicing_email']").val("");
            $("input[name='invoicing_phone']").val("");
            $("input[name='invoicing_street']").val("");
            $("input[name='invoicing_street2']").val("");
            $("input[name='invoicing_zip']").val("");
            $("input[name='invoicing_city']").val("");

            $("input[name='create_vendor_address']").val("yes");
            $("input[name='update_vendor_address']").val("no");
        });

        // Configuration du type de pièce //

        var price_model = new Model('of.worktop.configurator.price');
        var finishing_model = new Model('of.worktop.configurator.finishing');
        var color_model = new Model('of.worktop.configurator.color');
        var thickness_model = new Model('of.worktop.configurator.thickness');

        // Sélecteur matériau/finition
        $(oe_of_website_worktop_configurator).on('change', "select[name='material_id']", function () {
            clickwatch(function() {
                var material_id = $("select[name='material_id'] option:selected").val();
                var finishing_id = $("select[name='finishing_id'] option:selected").val();

                $("select[name='finishing_id']").empty();

                $("select[name='finishing_id']").append($('<option>', {
                    text: "Choisir une finition...",
                    value : ""
                }));

                if (material_id) {
                    ajax.jsonRpc("/worktop_configurator/get_pricelist", 'call').then(
                        function(pricelist) {
                            price_model.call("search_read", {
                                domain: [
                                    ["material_id", "=", parseInt(material_id)],
                                    ["pricelist_ids", "in", [parseInt(pricelist)]],
                                ],
                                fields: ["id", "finishing_id"]
                            }).done(function (prices) {
                                var finishing_list = [];
                                var finishing_id_list = [];
                                prices.forEach(function(prc) {
                                    if (!finishing_id_list.includes(prc['finishing_id'][0])) {
                                        finishing_id_list.push(prc['finishing_id'][0]);
                                        finishing_list.push(prc['finishing_id']);
                                    }
                                });

                                finishing_list.forEach(function(finishing) {
                                    $("select[name='finishing_id']").append($('<option>', {
                                        text: finishing[1],
                                        value : finishing[0]
                                    }));
                                });

                                if ( $("select[name='finishing_id'] option[value='" + finishing_id + "']").length > 0) {
                                    $("select[name='finishing_id']").val(finishing_id);
                                }
                                else{
                                    $("select[name='finishing_id']").val('');
                                }

                                $("select[name='finishing_id']").change();
                            });
                        }
                    );
                }
                else {
                    $("select[name='finishing_id']").val('');

                    $("select[name='finishing_id']").change();
                }

            }, 200);
        });

        // Sélecteur finition/couleur
        $(oe_of_website_worktop_configurator).on('change', "select[name='finishing_id']", function () {
            clickwatch(function() {
                var material_id = $("select[name='material_id'] option:selected").val();
                var finishing_id = $("select[name='finishing_id'] option:selected").val();
                var color_id = $("select[name='color_id'] option:selected").val();

                $("select[name='color_id']").empty();

                $("select[name='color_id']").append($('<option>', {
                    text: "Choisir une couleur...",
                    value : ""
                }));

                if (finishing_id) {
                    ajax.jsonRpc("/worktop_configurator/get_pricelist", 'call').then(
                        function(pricelist) {
                            price_model.call("search_read", {
                                domain: [
                                    ["material_id", "=", parseInt(material_id)],
                                    ["finishing_id", "=", parseInt(finishing_id)],
                                    ["pricelist_ids", "in", [parseInt(pricelist)]],
                                ],
                                fields: ["id", "color_ids"]
                            }).done(function (prices) {
                                var color_list = [];
                                var color_id_list = [];
                                var color_ids = [];
                                prices.forEach(function(prc) {
                                    prc['color_ids'].forEach(function(color_id) {
                                        color_ids.push(color_id)
                                    });
                                });
                                color_model.call('search_read', {
                                    domain: [['id', 'in', color_ids]],
                                    fields: ['name']
                                }).done(function (colors) {
                                    colors.forEach(function(color) {
                                        if (!color_id_list.includes(color.id)) {
                                            color_id_list.push(color.id);
                                            color_list.push([color.id, color.name]);
                                        }
                                    });

                                    color_list.forEach(function(color) {
                                        $("select[name='color_id']").append($('<option>', {
                                            text: color[1],
                                            value : color[0]
                                        }));
                                    });

                                    if ( $("select[name='color_id'] option[value='" + color_id + "']").length > 0) {
                                        $("select[name='color_id']").val(color_id);
                                    }
                                    else{
                                        $("select[name='color_id']").val('');
                                    }

                                    $("select[name='color_id']").change();

                                });
                            });
                        }
                    );
                }
                else {
                    $("select[name='color_id']").val('');

                    $("select[name='color_id']").change();
                }
            }, 200);
        });

        // Sélecteur couleur/thickness
        $(oe_of_website_worktop_configurator).on('change', "select[name='color_id']", function () {
            clickwatch(function() {
                var material_id = $("select[name='material_id'] option:selected").val();
                var finishing_id = $("select[name='finishing_id'] option:selected").val();
                var color_id = $("select[name='color_id'] option:selected").val();
                var thickness_id = $("select[name='thickness_id'] option:selected").val();

                $("select[name='thickness_id']").empty();

                $("select[name='thickness_id']").append($('<option>', {
                    text: "Choisir une épaisseur...",
                    value : ""
                }));

                if (color_id) {
                    ajax.jsonRpc("/worktop_configurator/get_pricelist", 'call').then(
                        function(pricelist) {
                            price_model.call("search_read", {
                                domain: [
                                    ["material_id", "=", parseInt(material_id)],
                                    ["finishing_id", "=", parseInt(finishing_id)],
                                    ["color_ids", "in", [parseInt(color_id)]],
                                    ["pricelist_ids", "in", [parseInt(pricelist)]],
                                ],
                                fields: ["id", "thickness_id"]
                            }).done(function (prices) {
                                var thickness_list = [];
                                var thickness_id_list = [];
                                prices.forEach(function(prc) {
                                    if (!thickness_id_list.includes(prc['thickness_id'][0])) {
                                        thickness_id_list.push(prc['thickness_id'][0]);
                                        thickness_list.push(prc['thickness_id']);
                                    }
                                });

                                thickness_list.forEach(function(thickness) {
                                    $("select[name='thickness_id']").append($('<option>', {
                                        text: thickness[1],
                                        value : thickness[0]
                                    }));
                                });

                                if ( $("select[name='thickness_id'] option[value='" + thickness_id + "']").length > 0) {
                                    $("select[name='thickness_id']").val(thickness_id);
                                }
                                else{
                                    $("select[name='thickness_id']").val('');
                                }
                            });
                        }
                    );
                }
                else {
                    $("select[name='thickness_id']").val('');
                }
            }, 200);
        });

        $("select[name='material_id']").change();

        // Affichage des images de couleur

        if ($("#color_id").val()) {
            ajax.jsonRpc("/worktop_configurator/get_color_image/" + $("#color_id").val(), 'call', {}).then(
                function(data) {
                    // manage fields order / visibility
                    if (data.image) {
                        var url = 'url("data:image/gif;base64,'+ data.image.replace(/(\r\n|\n|\r)/gm, "") +'")';
                        $("#color_image").css("background-image", url);
                        $("#color_image").css("border", "1px solid black");
                    }
                }
            );
        }

        $(oe_of_website_worktop_configurator).on('change', "select[name='color_id']", function () {
            if ($("#color_id").val()) {
                ajax.jsonRpc("/worktop_configurator/get_color_image/" + $("#color_id").val(), 'call', {}).then(
                    function(data) {
                        // manage fields order / visibility
                        if (data.image) {
                            var url = 'url("data:image/gif;base64,'+ data.image.replace(/(\r\n|\n|\r)/gm, "") +'")';
                            $("#color_image").css("background-image", url);
                            $("#color_image").css("border", "1px solid black");
                        }
                        else {
                            $("#color_image").css("background-image", "");
                            $("#color_image").css("border", "");
                        }
                    }
                );
            }
            else
            {
                $("#color_image").css("background-image", "");
                $("#color_image").css("border", "");
            }
        });

        // Mise à jour du prix

        function compute_price() {
            var material_id = $("select[name='material_id'] option:selected").val();
            var finishing_id = $("select[name='finishing_id'] option:selected").val();
            var color_id = $("select[name='color_id'] option:selected").val();
            var thickness_id = $("select[name='thickness_id'] option:selected").val();
            var length = $("input[name='length']").val();
            var width = $("input[name='width']").val();

            if (material_id && finishing_id && color_id && thickness_id && length && width) {
                ajax.jsonRpc("/worktop_configurator/get_pricelist", 'call').then(
                    function(pricelist) {
                        price_model.call("search",
                            [[
                                ["material_id", "=", parseInt(material_id)],
                                ["finishing_id", "=", parseInt(finishing_id)],
                                ["color_ids", "in", [parseInt(color_id)]],
                                ["thickness_id", "=", parseInt(thickness_id)],
                                ["pricelist_ids", "in", [parseInt(pricelist)]],
                            ]],
                            {limit: 1}
                        ).done(function (base_price) {
                            ajax.jsonRpc("/worktop_configurator/compute_price", 'call', {
                                base_price_id: base_price[0],
                                length: parseFloat(length),
                                width: parseFloat(width),
                                material_id: parseInt(material_id)}
                            ).then(
                                function(res) {
                                    $("span[name='price'] > span.oe_currency_value").text(res['price'].toFixed(2).toString().replace(/\d(?=(\d{3})+\.)/g, '$& ').replace(/\./g, ','));
                                    $("span[name='total_price'] > span.oe_currency_value").text(res['total_price'].toFixed(2).toString().replace(/\d(?=(\d{3})+\.)/g, '$& ').replace(/\./g, ','));
                                }
                            );
                        });
                    }
                );
            }
            else {
                $("span[name='price'] > span.oe_currency_value").text("0,00");
                $("span[name='total_price'] > span.oe_currency_value").text("0,00");
            }
        }

        $(oe_of_website_worktop_configurator).on('change', "select[name='material_id']", function () {
            compute_price()
        });

        $(oe_of_website_worktop_configurator).on('change', "select[name='finishing_id']", function () {
            compute_price()
        });

        $(oe_of_website_worktop_configurator).on('change', "select[name='color_id']", function () {
            compute_price()
        });

        $(oe_of_website_worktop_configurator).on('change', "select[name='thickness_id']", function () {
            compute_price()
        });

        $(oe_of_website_worktop_configurator).on('change', "input[name='length']", function () {
            compute_price()
        });

        $(oe_of_website_worktop_configurator).on('change', "input[name='width']", function () {
            compute_price()
        });

        // Devis //

        $('form.js_attributes input, form.js_attributes select', oe_of_website_worktop_configurator).on('change', function (event) {
            if (!event.isDefaultPrevented()) {
                $(this).closest("form").submit();
            }
        });

        // Ajout des articles dans le devis
        $(oe_of_website_worktop_configurator).on('click', '.of_js_add_to_quote', function() {
            var product_id = $(this).parents('div.product-img').find('#product_id').text();
            var product_price = $(this).parents('div.product-img').find('#product_price').text();
            event.preventDefault();
            ajax.jsonRpc("/worktop_configurator/product_modal", 'call', {
                'product_id': product_id,
                'price': product_price,
            }).then(function (modal) {
                var $modal = $(modal);

                // Affichage de la pop-up
                $(oe_of_website_worktop_configurator).addClass('css_options');
                $modal.appendTo($(oe_of_website_worktop_configurator))
                    .modal()
                    .on('hidden.bs.modal', function () {
                        $(oe_of_website_worktop_configurator).removeClass('css_options');
                        $(this).remove();
                    });

                // Modification des quantités
                $modal.on('click', 'a.js_add_cart_json', function (ev) {
                    ev.preventDefault();
                    var $link = $(ev.currentTarget);
                    var $input = $link.parent().find("input");
                    var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val() || 0, 10);
                    $('input[name="'+$input.attr("name")+'"]').val(quantity > 1 ? quantity : 1);
                    $input.change();
                    return false;
                });

                // Validation
                $modal.on('click', '.a-submit', function () {
                    var $a = $(this);
                    var product_id = $modal.find('span.oe_price[data-product-id]').data('product-id');
                    var product_price = $modal.find('input[name="product_price"]').val();
                    var quantity = $modal.find('input[name="add_qty"]').val();
                    ajax.jsonRpc("/worktop_configurator/add_product", 'call', {
                        'product_id': product_id,
                        'price': product_price,
                        'quantity': quantity,
                    }).then(function () {
                        $modal.modal('hide');
                    });
                });
            });
        });

        // Quantité des articles du devis
        $(oe_of_website_worktop_configurator).on("change", "input.js_quantity[data-product-id]", function () {
            var $input = $(this);
            if ($input.data('update_change') || $('body').hasClass('editor_enable')) {
                return;
            }
            var value = parseInt($input.val() || 0, 10);
            if (isNaN(value)) {
                value = 1;
            }
            var $dom = $(this).closest('tr');
            var line_id = parseInt($input.data('line-id'),10);
            clickwatch(function(){
                $input.data('update_change', true);

                ajax.jsonRpc("/worktop_configurator/quote_line/update_qty", 'call', {
                    'line_id': line_id,
                    'qty': value
                }).then(function (data) {
                    $input.data('update_change', false);
                    var check_value = parseInt($input.val() || 0, 10);
                    if (isNaN(check_value)) {
                        check_value = 1;
                    }
                    if (value !== check_value) {
                        $input.trigger('change');
                        return;
                    }
                    $input.val(data.quantity);
                    $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);
                    $(".js_quote_lines").first().before(data['of_website_worktop_configurator.quote_lines']).end().remove();
                });
            }, 500);
        });

        // Suppression des articles du devis
        $(oe_of_website_worktop_configurator).on('click', '.js_delete_product', function(e) {
            e.preventDefault();
            $(this).closest('tr').find('.js_quantity').val(0).trigger('change');
        });

    });
});
