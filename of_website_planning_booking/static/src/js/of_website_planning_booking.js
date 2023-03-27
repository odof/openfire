odoo.define('of_website_planning_booking.planning_website', function (require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var utils = require('web.utils');
    var core = require('web.core');
    var config = require('web.config');
    var _t = core._t;
    var Model = require('web.Model');


    if(!$('.oe_website_sale').length) {
        return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
    }

    $('.oe_website_sale').each(function () {
        var oe_website_sale = this;

        var clickwatch = (function(){
            var timer = 0;
            return function(callback, ms){
                clearTimeout(timer);
                timer = setTimeout(callback, ms);
            };
        })();


        $('.oe_website_sale .a-submit, #comment .a-submit').off('click').on('click', function (event) {
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
        $('form.js_attributes input, form.js_attributes select', oe_website_sale).on('change', function (event) {
            if (!event.isDefaultPrevented()) {
                $(this).closest("form").submit();
            }
        });
        $('select#service_id', oe_website_sale).on('change', function (event) {
            // Quand on selectionne le contrat, on vient affecter la prestation qui va avec
            var tache_selector = $('select#tache_id');
            var service_id = parseInt(this[this.selectedIndex].value);
            var service_model = new Model('of.service');
            if (service_id != null && service_id != undefined) {
                service_model.call('read', [service_id, ['tache_id']], {}).done(function (result) {
                    if (result.length > 0) {
                        tache_selector.val(result[0]['tache_id'][0].toString())
                    }
                });
            };
        });

        // hightlight selected color
        $('.css_attribute_color input', oe_website_sale).on('change', function () {
            $('.css_attribute_color').removeClass("active");
            $('.css_attribute_color:has(input:checked)').addClass("active");
        });

        $('.oe_cart').on('click', '.of_js_change_shipping', function() {
            if (!$('body.editor_enable').length) { //allow to edit button text with editor
                var $old = $('.all_shipping').find('.panel.of_border_primary');
                $old.find('.btn-ship').toggle();
                $old.addClass('of_js_change_shipping');
                $old.removeClass('of_border_primary');

                var $new = $(this).parent('div.one_kanban').find('.panel');
                $new.find('.btn-ship').toggle();
                $new.removeClass('of_js_change_shipping');
                $new.addClass('of_border_primary');

                var $form = $(this).parent('div.one_kanban').find('form.hide');
                $.post($form.attr('action'), $form.serialize()+'&xhr=1');
            }
        });
        $('.oe_cart').on('click', '.of_js_edit_address', function() {
            $(this).parent('div.one_kanban').find('form.hide').attr('action', '/new_booking/address_create_edit').submit();
        });

        if ($('.oe_website_sale .dropdown_sorty_by').length) {
            // this method allow to keep current get param from the action, with new search query
            $('.oe_website_sale .o_website_sale_search').on('submit', function (event) {
                var $this = $(this);
                if (!event.isDefaultPrevented() && !$this.is(".disabled")) {
                    event.preventDefault();
                    var oldurl = $this.attr('action');
                    oldurl += (oldurl.indexOf("?")===-1) ? "?" : "";
                    var search = $this.find('input.search-query');
                    window.location = oldurl + '&' + search.attr('name') + '=' + encodeURIComponent(search.val());
                }
            });
        }

        if ($(".checkout_autoformat").length) {
            $(oe_website_sale).on('change', "select[name='country_id']", function () {
                clickwatch(function() {
                    if ($("#country_id").val()) {
                        ajax.jsonRpc("/shop/country_infos/" + $("#country_id").val(), 'call', {mode: 'shipping'}).then(
                            function(data) {
                                // placeholder phone_code
                                //$("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

                                // populate states and display
                                var selectStates = $("select[name='state_id']");
                                // dont reload state at first loading (done in qweb)
                                if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                                    if (data.states.length) {
                                        selectStates.html('');
                                        _.each(data.states, function(x) {
                                            var opt = $('<option>').text(x[1])
                                                .attr('value', x[0])
                                                .attr('data-code', x[2]);
                                            selectStates.append(opt);
                                        });
                                        selectStates.parent('div').show();
                                    }
                                    else {
                                        selectStates.val('').parent('div').hide();
                                    }
                                    selectStates.data('init', 0);
                                }
                                else {
                                    selectStates.data('init', 0);
                                }

                                // manage fields order / visibility
                                if (data.fields) {
                                    if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)){
                                        $(".div_zip").before($(".div_city"));
                                    }
                                    else {
                                        $(".div_zip").after($(".div_city"));
                                    }
                                    var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                                    _.each(all_fields, function(field) {
                                        $(".checkout_autoformat .div_" + field.split('_')[0]).toggle($.inArray(field, data.fields)>=0);
                                    });
                                }
                            }
                        );
                    }
                }, 500);
            });
        }
        $("select[name='country_id']").change();

        // Manage extra brand visibility
        if ($(".booking_extra_brand").length) {
            $(oe_website_sale).on('change', "select[name='brand_id']", function () {
                clickwatch(function() {
                    if ($("#brand_id").val() == 'Autre marque') {
                        $(".div_brand").addClass('col-md-5');
                        $(".div_brand").removeClass('col-md-10');
                        $(".div_extra_brand").show();
                    }
                    else {
                        $(".div_brand").addClass('col-md-10');
                        $(".div_brand").removeClass('col-md-5');
                        $(".div_extra_brand").hide();
                        $("input[name='extra_brand']").val('').trigger('change');
                    }
                }, 500);
            });
        }
    });

    $('.of_rdv_nouveau_tous_creneaux').on('click', '.of_js_change_creneau', function() {
        if (!$('body.editor_enable').length) { //allow to edit button text with editor
            var $old = $('.of_rdv_nouveau_tous_creneaux').find('.panel.of_border_primary');
            $old.find('.btn-ship').toggle();
            $old.addClass('of_js_change_creneau');
            $old.removeClass('of_border_primary');

            var $new = $(this).parent('div.one_kanban').find('.panel');
            $new.find('.btn-ship').toggle();
            $new.removeClass('of_js_change_creneau');
            $new.addClass('of_border_primary');

            var $form = $(this).parent('div.one_kanban').find('form.hide');
            $.post($form.attr('action'), $form.serialize()+'&xhr=1');
        }
    });

    // GPS Video Pop-up
    $("[data-media]").on("click", function(e) {
        e.preventDefault();
        var $this = $(this);
        var videoUrl = $this.attr("data-media");
        var popup = $this.attr("href");
        var $popupIframe = $(popup).find("iframe");

        $popupIframe.attr("src", videoUrl);

        $this.closest(".container").addClass("show-popup");
    });

    $(".popup").on("click", function(e) {
        e.preventDefault();
        e.stopPropagation();

        $('.yt_player_iframe').each(function(){
            this.contentWindow.postMessage('{"event":"command","func":"stopVideo","args":""}', '*')
        });
        $(".container").removeClass("show-popup");
    });

    $(".popup > iframe").on("click", function(e) {
        e.stopPropagation();
    });
});

odoo.define('of_website_planning_booking.map_localisation', function (require) {
    'use strict';

    var website = require('website.website');
    var ajax = require('web.ajax');

    if (!$('.div_map_planning_booking').length) {
        return $.Deferred().reject("DOM doesn't contain '.div_map_planning_booking'");
    }

    var infoWindow = new google.maps.InfoWindow();
    var markers = [];
    var content = '';
    var icon = false;
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 18,
        maxZoom: 25,
        center: new google.maps.LatLng(map_data[0].geo_lat, map_data[0].geo_lng),
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });
    var marker = new google.maps.MarkerImage('https://mt.googleapis.com/vt/icon/name=icons/spotlight/spotlight-poi.png&scale=1', new google.maps.Size(15, 15));

    var onMouseOver = function () {
        var marker = this;
        var object = marker.object;
        content = '<div class="marker">' + '<b>' + object.name.replace(/\n/g, "<br />") + '</b></div>'
        infoWindow.setContent(content);
        infoWindow.open(map, marker);
    };

    var set_marker = function (object, point) {
        var latLng = new google.maps.LatLng(object.geo_lat, object.geo_lng);
        var marker = new google.maps.Marker({
            object: object,
            icon: point,
            map: map,
            position: latLng
        });
        google.maps.event.addListener(marker, 'mouseover', onMouseOver);
        google.maps.event.addListener(marker, 'mouseout', function() {infoWindow.close();});
        markers.push(marker);
    };

    if (map_data) {
        set_marker(map_data[0], marker);
    }

});
