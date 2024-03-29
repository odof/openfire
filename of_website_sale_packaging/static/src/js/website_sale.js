odoo.define('website_sale.cart', function(require) {
    "use strict";

    var base = require('web_editor.base');
    var core = require('web.core');
    var utils = require('web.utils');
    var _t = core._t;

    var shopping_cart_link = $('ul#top_menu li a[href$="/shop/cart"]');
    var shopping_cart_link_counter;
    shopping_cart_link.popover({
        trigger: 'manual',
        animation: true,
        html: true,
        title: function() {
            return _t("My Cart");
        },
        container: 'body',
        placement: 'auto',
        template: '<div class="popover mycart-popover" role="tooltip"><div class="arrow"></div><h3 class="popover-title"></h3><div class="popover-content"></div></div>'
    }).on("mouseenter", function() {
        var self = this;
        clearTimeout(shopping_cart_link_counter);
        shopping_cart_link.not(self).popover('hide');
        shopping_cart_link_counter = setTimeout(function() {
            if ($(self).is(':hover') && !$(".mycart-popover:visible").length) {
                $.get("/shop/cart", {
                        'type': 'popover'
                    })
                    .then(function(data) {
                        $(self).data("bs.popover").options.content = data;
                        $(self).popover("show");
                        $(".popover").on("mouseleave", function() {
                            $(self).trigger('mouseleave');
                        });
                    });
            }
        }, 100);
    }).on("mouseleave", function() {
        var self = this;
        setTimeout(function() {
            if (!$(".popover:hover").length) {
                if (!$(self).is(':hover')) {
                    $(self).popover('hide');
                }
            }
        }, 1000);
    });
});

odoo.define('website_sale.website_sale_category', function(require) {
    "use strict";

    var base = require('web_editor.base');

    if (!$('#o_shop_collapse_category').length) {
        return $.Deferred().reject("DOM doesn't contain '#o_shop_collapse_category'");
    }

    $('#o_shop_collapse_category').on('click', '.fa-chevron-right', function() {
        $(this).parent().siblings().find('.fa-chevron-down:first').click();
        $(this).parents('li').find('ul:first').show('normal');
        $(this).toggleClass('fa-chevron-down fa-chevron-right');
    });

    $('#o_shop_collapse_category').on('click', '.fa-chevron-down', function() {
        $(this).parent().find('ul:first').hide('normal');
        $(this).toggleClass('fa-chevron-down fa-chevron-right');
    });
});

odoo.define('website_sale.website_sale', function(require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var utils = require('web.utils');
    var core = require('web.core');
    var config = require('web.config');
    var _t = core._t;

    if (!$('.oe_website_sale').length) {
        return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
    }

    $('.oe_website_sale').each(function() {
        var oe_website_sale = this;

        $(oe_website_sale).on("change", 'input[name="add_qty"]', function(event) {

            var product_ids = [];
            var product_dom = $(".js_product .js_add_cart_variants[data-attribute_value_ids]");
            if (!product_dom.length || $('body').hasClass('editor_enable')) {
                return;
            }
            var $input = $(event.currentTarget);
            var qty = $input.val();

            // Si il y a plusieurs input (par ex: modal)
            var $all_input = $('input[name="'+$input.attr("name")+'"]');
            var packaging_unit = $(event.target).closest('*:has(input[name="packaging_unit"])').find('input[name="packaging_unit"]');

            if (qty <= 0) {
                qty = 1.0;
                $all_input.val(qty);
            }

            // Si cet article supporte le conditionnement, on l'arrondi en fonction de l'unité de conditionnement
            if (packaging_unit.length) {
                var round = parseFloat(packaging_unit.val());
                qty = parseFloat(qty);
                var remainder = qty % round;

                if(!utils.float_is_zero(remainder, 4)) {
                    qty = qty + round - remainder;
                    $all_input.val(qty.toFixed(2));
                }
            } else {
                qty = Math.floor(qty);
                $all_input.val(qty);
            }

            _.each(product_dom, function(prod) {
                _.each($(prod).data("attribute_value_ids"), function(entry) {
                    if (product_ids.indexOf(entry[0]) === -1) {
                        product_ids.push(entry[0]);
                    }
                });
            });

            if ($("#product_detail").length) {
                // display the reduction from the pricelist in function of the quantity
                ajax.jsonRpc("/shop/get_unit_price", 'call', {
                        'product_ids': product_ids,
                        'add_qty': parseFloat(qty)
                    })
                    .then(function(data) {
                        _.each(product_dom, function(prod) {
                            var current = $(prod).data("attribute_value_ids");
                            for (var j = 0; j < current.length; j++) {
                                current[j][2] = data[current[j][0]];
                            }
                            $(prod).trigger("change");
                        });
                    });
            }
        });

        // change for css
        $(oe_website_sale).on('mouseup touchend', '.js_publish', function(ev) {
            $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
        });

        var clickwatch = (function() {
            var timer = 0;
            return function(callback, ms) {
                clearTimeout(timer);
                timer = setTimeout(callback, ms);
            };
        })();

        $(oe_website_sale).on("change", ".oe_cart input.js_quantity[data-product-id]", function() {
            var $input = $(this);
            if ($input.data('update_change') || $('body').hasClass('editor_enable')) {
                return;
            }
            var value = parseFloat($input.val() || 0, 10);
            if (isNaN(value)) {
                value = 1;
            }
            var $dom = $(this).closest('tr');
            var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
            var line_id = parseInt($input.data('line-id'), 10);
            var packaging_unit = parseFloat($input.data('packaging-unit'), 10);
            var product_ids = [parseInt($input.data('product-id'), 10)];

            if (value < 0 && !utils.float_is_zero(value, 4)) {
                value = 1.0;
                $input.val(value);
            }

            if (packaging_unit) {
                var round = parseFloat(packaging_unit);
                var remainder = (value % round).toFixed(2);
                if(!utils.float_is_zero(remainder, 4)) {
                    value = (value + round - remainder).toFixed(2);
                    $input.val(value);
                }
            } else {
                value = Math.floor(value);
                $input.val(value);
            }

            clickwatch(function() {
                $dom_optional.each(function() {
                    $(this).find('.js_quantity').text(value);
                    product_ids.push($(this).find('span[data-product-id]').data('product-id'));
                });
                $input.data('update_change', true);

                ajax.jsonRpc("/shop/cart/update_json", 'call', {
                    'line_id': line_id,
                    'product_id': parseInt($input.data('product-id'), 10),
                    'set_qty': value
                }).then(function(data) {
                    $input.data('update_change', false);
                    var check_value = parseFloat($input.val() || 0, 10);
                    if (isNaN(check_value)) {
                        check_value = 1;
                    }
                    if (value !== check_value) {
                        $input.trigger('change');
                        return;
                    }
                    var $q = $(".my_cart_quantity");
                    if (data.cart_quantity) {
                        $q.parents('li:first').removeClass("hidden");
                    } else {
                        $q.parents('li:first').addClass("hidden");
                        $('a[href*="/shop/checkout"]').addClass("hidden");
                    }

                    $q.html(data.cart_quantity).hide().fadeIn(600);
                    $input.val(data.quantity);
                    $('.js_quantity[data-line-id=' + line_id + ']').val(data.quantity).html(data.quantity);

                    $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();

                    if (data.warning) {
                        var cart_alert = $('.oe_cart').parent().find('#data_warning');
                        if (cart_alert.length === 0) {
                            $('.oe_cart').prepend('<div class="alert alert-danger alert-dismissable" role="alert" id="data_warning">' +
                                '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning + '</div>');
                        } else {
                            cart_alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning);
                        }
                        $input.val(data.quantity);
                    }
                });
            }, 500);
        });

        $(oe_website_sale).on("click", ".oe_cart a.js_add_suggested_products", function() {
            $(this).prev('input').val(1).trigger('change');
        });

        // hack to add and remove from cart with json
        $(oe_website_sale).on('click', 'a.js_add_cart_json', function(ev) {
            if ($('body').hasClass('editor_enable')) {
                return;
            }
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var $input = $link.parent().find("input");

            // Si il y a plusieurs input (par ex: modal)
            var $all_input = $('input[name="'+$input.attr("name")+'"]');

            var product_id = +$input.closest('*:has(input[name="product_id"])').find('input[name="product_id"]').val();
            var packaging_unit = +$input.closest('*:has(input[name="packaging_unit"])').find('input[name="packaging_unit"]').val();
            if (!packaging_unit) {
                packaging_unit = parseFloat($input.data('packaging-unit'), 10);
            }
            var min = parseFloat($input.data("min") || 0);
            var max = parseFloat($input.data("max") || Infinity);
            var sign = ($link.has(".fa-minus").length ? -1 : 1);
            if (packaging_unit) {
                sign = sign * parseFloat(packaging_unit);
            }
            var quantity = sign + parseFloat($input.val() || 0, 10);
            quantity = quantity.toFixed(2);

            $all_input.add($input).filter(function() {
                var $prod = $(this).closest('*:has(input[name="product_id"])');
                return !$prod.length || +$prod.find('input[name="product_id"]').val() === product_id;
            }).val(quantity > min ? (quantity < max ? quantity : max) : min);
            $input.change();
            return false;
        });

        $('.oe_website_sale .a-submit, #comment .a-submit').off('click').on('click', function(event) {
            if (!event.isDefaultPrevented() && !$(this).is(".disabled")) {
                $(this).closest('form').submit();
            }
            if ($(this).hasClass('a-submit-disable')) {
                $(this).addClass("disabled");
            }
            if ($(this).hasClass('a-submit-loading')) {
                var loading = '<span class="fa fa-cog fa-spin"/>';
                var fa_span = $(this).find('span[class*="fa"]');
                if (fa_span.length) {
                    fa_span.replaceWith(loading);
                } else {
                    $(this).append(loading);
                }
            }
        });
        $('form.js_attributes input, form.js_attributes select', oe_website_sale).on('change', function(event) {
            if (!event.isDefaultPrevented()) {
                $(this).closest("form").submit();
            }
        });

        // change price when they are variants
        $('form.js_add_cart_json label', oe_website_sale).on('mouseup touchend', function() {
            var $label = $(this);
            var $price = $label.parents("form:first").find(".oe_price .oe_currency_value");
            if (!$price.data("price")) {
                $price.data("price", parseFloat($price.text()));
            }
            var value = $price.data("price") + parseFloat($label.find(".badge span").text() || 0);

            var dec = value % 1;
            $price.html(value + (dec < 0.01 ? ".00" : (dec < 1 ? "0" : "")));
        });
        // hightlight selected color
        $('.css_attribute_color input', oe_website_sale).on('change', function() {
            $('.css_attribute_color').removeClass("active");
            $('.css_attribute_color:has(input:checked)').addClass("active");
        });

        function price_to_str(price) {
            var l10n = _t.database.parameters;
            var precision = 2;

            if ($(".decimal_precision").length) {
                precision = parseInt($(".decimal_precision").last().data('precision'));
                if (!precision) {
                    precision = 0;
                } //todo: remove me in master/saas-17
            }
            var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
            formatted[0] = utils.insert_thousand_seps(formatted[0]);
            return formatted.join(l10n.decimal_point);
        }

        function update_product_image(event_source, product_id) {
            if ($('#o-carousel-product').length) {
                var $img = $(event_source).closest('tr.js_product, .oe_website_sale').find('img.js_variant_img');
                $img.attr("src", "/web/image/product.product/" + product_id + "/image");
                $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
                    .data('oe-model', 'product.product').data('oe-id', product_id);

                var $thumbnail = $(event_source).closest('tr.js_product, .oe_website_sale').find('img.js_variant_img_small');
                if ($thumbnail.length !== 0) { // if only one, thumbnails are not displayed
                    $thumbnail.attr("src", "/web/image/product.product/" + product_id + "/image/90x90");
                    $('.carousel').carousel(0);
                }
            } else {
                var $img = $(event_source).closest('tr.js_product, .oe_website_sale').find('span[data-oe-model^="product."][data-oe-type="image"] img:first, img.product_detail_img');
                $img.attr("src", "/web/image/product.product/" + product_id + "/image");
                $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
                    .data('oe-model', 'product.product').data('oe-id', product_id);
            }
            // reset zooming constructs
            $img.filter('[data-zoom-image]').attr('data-zoom-image', $img.attr('src'));
            if ($img.data('zoomOdoo') !== undefined) {
                $img.data('zoomOdoo').isReady = false;
            }
        }

        $(oe_website_sale).on('change', 'input.js_product_change', function() {
            var self = this;
            var $parent = $(this).closest('.js_product');
            $.when(base.ready()).then(function() {
                $parent.find(".oe_default_price:first .oe_currency_value").html(price_to_str(+$(self).data('lst_price')));
                $parent.find(".oe_price:first .oe_currency_value").html(price_to_str(+$(self).data('price')));
            });
            update_product_image(this, +$(this).val());
        });

        $(oe_website_sale).on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function(ev) {
            var $ul = $(ev.target).closest('.js_add_cart_variants');
            var $parent = $ul.closest('.js_product');
            var $product_id = $parent.find('.product_id').first();
            var $price = $parent.find(".oe_price:first .oe_currency_value");
            var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
            var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
            var variant_ids = $ul.data("attribute_value_ids");
            var values = [];
            var unchanged_values = $parent.find('div.oe_unchanged_value_ids').data('unchanged_value_ids') || [];

            $parent.find('input.js_variant_change:checked, select.js_variant_change').each(function() {
                values.push(+$(this).val());
            });
            values = values.concat(unchanged_values);

            $parent.find("label").removeClass("text-muted css_not_available");

            var product_id = false;
            for (var k in variant_ids) {
                if (_.isEmpty(_.difference(variant_ids[k][1], values))) {
                    $.when(base.ready()).then(function() {
                        $price.html(price_to_str(variant_ids[k][2]));
                        $default_price.html(price_to_str(variant_ids[k][3]));
                    });
                    if (variant_ids[k][3] - variant_ids[k][2] > 0.01) {
                        $default_price.closest('.oe_website_sale').addClass("discount");
                        $optional_price.closest('.oe_optional').show().css('text-decoration', 'line-through');
                        $default_price.parent().removeClass('hidden');
                    } else {
                        $optional_price.closest('.oe_optional').hide();
                        $default_price.parent().addClass('hidden');
                    }
                    product_id = variant_ids[k][0];
                    update_product_image(this, product_id);
                    break;
                }
            }

            $parent.find("input.js_variant_change:radio, select.js_variant_change").each(function() {
                var $input = $(this);
                var id = +$input.val();
                var values = [id];

                $parent.find("ul:not(:has(input.js_variant_change[value='" + id + "'])) input.js_variant_change:checked, select.js_variant_change").each(function() {
                    values.push(+$(this).val());
                });

                for (var k in variant_ids) {
                    if (!_.difference(values, variant_ids[k][1]).length) {
                        return;
                    }
                }
                $input.closest("label").addClass("css_not_available");
                $input.find("option[value='" + id + "']").addClass("css_not_available");
            });

            if (product_id) {
                $parent.removeClass("css_not_available");
                $product_id.val(product_id);
                $parent.find("#add_to_cart").removeClass("disabled");
            } else {
                $parent.addClass("css_not_available");
                $product_id.val(0);
                $parent.find("#add_to_cart").addClass("disabled");
            }
        });

        $('div.js_product', oe_website_sale).each(function() {
            $('input.js_product_change', this).first().trigger('change');
        });

        $('.js_add_cart_variants', oe_website_sale).each(function() {
            $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
        });

        $('.oe_cart').on('click', '.js_change_shipping', function() {
            if (!$('body.editor_enable').length) { //allow to edit button text with editor
                var $old = $('.all_shipping').find('.panel.border_primary');
                $old.find('.btn-ship').toggle();
                $old.addClass('js_change_shipping');
                $old.removeClass('border_primary');

                var $new = $(this).parent('div.one_kanban').find('.panel');
                $new.find('.btn-ship').toggle();
                $new.removeClass('js_change_shipping');
                $new.addClass('border_primary');

                var $form = $(this).parent('div.one_kanban').find('form.hide');
                $.post($form.attr('action'), $form.serialize() + '&xhr=1');
            }
        });
        $('.oe_cart').on('click', '.js_edit_address', function() {
            $(this).parent('div.one_kanban').find('form.hide').attr('action', '/shop/address').submit();
        });
        $('.oe_cart').on('click', '.js_delete_product', function(e) {
            e.preventDefault();
            $(this).closest('tr').find('.js_quantity').val(0).trigger('change');
        });

        if ($('.oe_website_sale .dropdown_sorty_by').length) {
            // this method allow to keep current get param from the action, with new search query
            $('.oe_website_sale .o_website_sale_search').on('submit', function(event) {
                var $this = $(this);
                if (!event.isDefaultPrevented() && !$this.is(".disabled")) {
                    event.preventDefault();
                    var oldurl = $this.attr('action');
                    oldurl += (oldurl.indexOf("?") === -1) ? "?" : "";
                    var search = $this.find('input.search-query');
                    window.location = oldurl + '&' + search.attr('name') + '=' + encodeURIComponent(search.val());
                }
            });
        }

        if ($(".checkout_autoformat").length) {
            $(oe_website_sale).on('change', "select[name='country_id']", function() {
                clickwatch(function() {
                    if ($("#country_id").val()) {
                        ajax.jsonRpc("/shop/country_infos/" + $("#country_id").val(), 'call', {
                            mode: 'shipping'
                        }).then(
                            function(data) {
                                // placeholder phone_code
                                //$("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

                                // populate states and display
                                var selectStates = $("select[name='state_id']");
                                // dont reload state at first loading (done in qweb)
                                if (selectStates.data('init') === 0 || selectStates.find('option').length === 1) {
                                    if (data.states.length) {
                                        selectStates.html('');
                                        _.each(data.states, function(x) {
                                            var opt = $('<option>').text(x[1])
                                                .attr('value', x[0])
                                                .attr('data-code', x[2]);
                                            selectStates.append(opt);
                                        });
                                        selectStates.parent('div').show();
                                    } else {
                                        selectStates.val('').parent('div').hide();
                                    }
                                    selectStates.data('init', 0);
                                } else {
                                    selectStates.data('init', 0);
                                }

                                // manage fields order / visibility
                                if (data.fields) {
                                    if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)) {
                                        $(".div_zip").before($(".div_city"));
                                    } else {
                                        $(".div_zip").after($(".div_city"));
                                    }
                                    var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                                    _.each(all_fields, function(field) {
                                        $(".checkout_autoformat .div_" + field.split('_')[0]).toggle($.inArray(field, data.fields) >= 0);
                                    });
                                }
                            }
                        );
                    }
                }, 500);
            });
        }
        $("select[name='country_id']").change();
    });

    // Deactivate image zoom for mobile devices, since it might prevent users to scroll
    if (config.device.size_class > config.device.SIZES.XS) {
        $('.ecom-zoomable img[data-zoom]').zoomOdoo({
            attach: '#o-carousel-product'
        });
    }
});