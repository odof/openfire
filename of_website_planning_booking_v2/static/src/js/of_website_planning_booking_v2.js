odoo.define('of_website_planning_booking_v2.of_booking', function (require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var website = require('website.website');
    var QWeb = core.qweb;

    function isValid(value) {
        return value != null && value != undefined && value != "" && !Number.isNaN(value);
    }

    if(!$('.of_booking_main').length) {
        return $.Deferred().reject("DOM doesn't contain '.of_booking_main'");
    }

    $('.of_booking_main').each(function () {
        var of_booking = this;
        var service_panel = $('div#service_panel', of_booking);
        var contract_panel = $('div#contract_panel', of_booking);
        var address_panel = $('div#address_panel', of_booking);
        var address_select = $('div#address_select', of_booking);
        var slot_panel = $('div#slot_panel', of_booking);
        var slots_div = $('div#slots_div', of_booking);
        var no_slot_div = $('div#no_slot_div', of_booking);
        var booking_slots_div = $('div#of_booking_slots', of_booking);
        var slot_error = $('div#slot_error', of_booking);

        var popup_text = $("span#popup-text");

        var service_selector = $('select#service_id', of_booking);

        var contract_selector = $('select#contract_id', of_booking);

        var address_selector = $('select#address_id', of_booking);
        var name_input = $('input#name', of_booking);
        var email_input = $('input#email', of_booking);
        var phone_input = $('input#phone', of_booking);
        var street_input = $('input#street', of_booking);
        var street2_input = $('input#street2', of_booking);
        var zip_id_input = $('input#zip_id', of_booking);
        var zip_input = $('input#zip', of_booking);
        var city_input = $('input#city', of_booking);

        var from_date_input = $('input#from_date', of_booking);

        var logged_partner_id = $('input#logged_partner_id', of_booking).val();

        var intervention_id = $('input#intervention_id', of_booking).val();
        var upd_service_id = $('input#upd_service_id', of_booking).val();
        var upd_contract_id = $('input#upd_contract_id', of_booking).val();
        var upd_address_id = $('input#upd_address_id', of_booking).val();

        ajax.loadXML('/of_website_planning_booking_v2/static/src/xml/of_booking_slot_kanban.xml', QWeb);

        var session_mode = "";
        var session_service_id = "";
        var session_contract_id = ""
        var session_partner_id = "";
        var session_from_date = "";
        var params = new URLSearchParams(window.location.search);

        $('.panel-collapse').on('show.bs.collapse', function () {
            $(this).siblings('.panel-heading').addClass('active');
        });

        $('.panel-collapse').on('hide.bs.collapse', function () {
            $(this).siblings('.panel-heading').removeClass('active');
        });

        if (params.get('of_return') == "1") {
            session_mode = sessionStorage.getItem('of_booking_mode');
            session_service_id = sessionStorage.getItem('of_booking_service_id');
            session_contract_id = sessionStorage.getItem('of_booking_contract_id');
            session_partner_id = sessionStorage.getItem('of_booking_partner_id');
            session_from_date = sessionStorage.getItem('of_booking_from_date');

            var newUrl = new URL(window.location.href);
            newUrl.searchParams.delete('of_return');
            history.replaceState({}, null, newUrl.href);
        }
        else if (isValid(intervention_id)) {
            if (isValid(upd_contract_id)) {
                sessionStorage.setItem('of_booking_mode', 'contract');
                sessionStorage.setItem('of_booking_contract_id', upd_contract_id);
                sessionStorage.removeItem('of_booking_service_id');
            }
            else {
                sessionStorage.setItem('of_booking_mode', 'service');
                sessionStorage.setItem('of_booking_service_id', upd_service_id);
                sessionStorage.removeItem('of_booking_contract_id');
            }

            sessionStorage.setItem('of_booking_partner_id', upd_address_id);
            sessionStorage.removeItem('of_booking_from_date');

            session_mode = sessionStorage.getItem('of_booking_mode');
            session_service_id = sessionStorage.getItem('of_booking_service_id');
            session_contract_id = sessionStorage.getItem('of_booking_contract_id');
            session_partner_id = sessionStorage.getItem('of_booking_partner_id');
        }
        else {
            sessionStorage.removeItem('of_booking_mode');
            sessionStorage.removeItem('of_booking_service_id');
            sessionStorage.removeItem('of_booking_contract_id');
            sessionStorage.removeItem('of_booking_partner_id');
            sessionStorage.removeItem('of_booking_from_date');
        }

        if (session_mode == null || session_mode == undefined || session_mode == "") {
            if (logged_partner_id != 0) {
                if ($('select#contract_id option', of_booking).length > 1) {
                    session_mode = 'contract';
                    address_select.hide();
                }
                else {
                    session_mode = 'service';
                }
            }
            else {
                session_mode = 'service';
                address_select.hide();
            }
            sessionStorage.setItem('of_booking_mode', session_mode);
        }

        if (session_mode == 'service') {
            contract_panel.hide();
            service_panel.show();

            if (isValid(session_service_id)) {
                service_selector.val(session_service_id)
                service_panel.find('.panel-collapse').collapse('hide');
                address_panel.show();
                if (!isValid(session_partner_id)) {
                    address_panel.find('.panel-collapse').collapse('show');
                }
            }
            else {
                service_panel.find('.panel-collapse').collapse('show');
                service_selector.val("");
            }

            if ($('select#address_id option', of_booking).length > 1) {
                address_select.show();
            }
            else {
                address_select.hide();
            }
        }
        else if (session_mode == 'contract') {
            contract_panel.show();
            service_panel.hide();

            if (isValid(session_contract_id)) {
                contract_selector.val(session_contract_id)
                contract_panel.find('.panel-collapse').collapse('hide');
                address_panel.show();
                if (!isValid(session_partner_id)) {
                    address_panel.find('.panel-collapse').collapse('show');
                }
            }
            else {
                contract_panel.find('.panel-collapse').collapse('show');
                contract_selector.val("");
            }

            address_select.hide();
        }

        if (session_from_date != null && session_from_date != undefined && session_from_date != "") {
            from_date_input.val(session_from_date);
        }
        else {
            var tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            var tomorrow_str = moment(tomorrow).format('YYYY-MM-DD');
            from_date_input.val(tomorrow_str);
        }

        if (isValid(session_partner_id)) {
            ajax.jsonRpc('/booking/get_partner', 'call', {
                'partner_id': session_partner_id
            }).then(function (result) {
                var partner = JSON.parse(result);
                name_input.val(partner.name);
                email_input.val(partner.email);
                phone_input.val(partner.phone);
                street_input.val(partner.street);
                street2_input.val(partner.street2 || "");
                zip_input.val(partner.zip);
                city_input.val(partner.city);

                address_selector.val(session_partner_id);

                address_panel.find('.panel-collapse').collapse('hide');

                slot_panel.show();
                slot_panel.find('.panel-collapse').collapse('show');

                from_date_input.change();
            }).fail(function() {
                window.location.href = "/booking/error";
            });
        }

        $('#my_contracts').on('click', function (event) {
            session_mode = 'contract';
            sessionStorage.setItem('of_booking_mode', session_mode);
            sessionStorage.removeItem('of_booking_service_id');
            service_selector.val("");
            service_panel.hide();
            service_panel.find('.panel-collapse').collapse('hide');
            contract_panel.show();
            contract_panel.find('.panel-collapse').collapse('show');
            address_select.hide();
            address_panel.hide();
            address_panel.find('.panel-collapse').collapse('hide');
            slot_panel.hide();
            slot_panel.find('.panel-collapse').collapse('hide');
        });

        $('#other_services').on('click', function (event) {
            session_mode = 'service';
            sessionStorage.setItem('of_booking_mode', session_mode);
            sessionStorage.removeItem('of_booking_contract_id');
            contract_selector.val("");
            service_panel.show();
            service_panel.find('.panel-collapse').collapse('show');
            contract_panel.hide();
            contract_panel.find('.panel-collapse').collapse('hide');
            if ($('select#address_id option', of_booking).length > 1) {
                address_select.show();
            }
            else {
                address_select.hide();
            }
            address_panel.hide();
            address_panel.find('.panel-collapse').collapse('hide');
            slot_panel.hide();
            slot_panel.find('.panel-collapse').collapse('hide');
        });

        service_selector.on('change', function (event) {
            var service_id = service_selector.find(":selected").val();
            if (isValid(service_id)) {
                sessionStorage.setItem('of_booking_service_id', service_id);
                session_service_id = service_id;

                service_selector.parent().removeClass('has-error');
                service_panel.find('.panel-collapse').collapse('hide');

                address_panel.show();
                address_panel.find('.panel-collapse').collapse('show');

                if (!isValid(session_partner_id)) {
                    if (logged_partner_id != 0) {
                        ajax.jsonRpc('/booking/get_partner', 'call', {
                            'partner_id': logged_partner_id
                        }).then(function (result) {
                            var partner = JSON.parse(result);
                            name_input.val(partner.name);
                            email_input.val(partner.email);
                            phone_input.val(partner.phone);
                            street_input.val(partner.street);
                            street2_input.val(partner.street2 || "");
                            zip_input.val(partner.zip);
                            city_input.val(partner.city);

                            address_selector.val(logged_partner_id);

                            sessionStorage.setItem('of_booking_partner_id', logged_partner_id);
                        }).fail(function() {
                            window.location.href = "/booking/error";
                        });
                    }
                }
                else if (logged_partner_id != 0 && logged_partner_id != session_partner_id) {
                    ajax.jsonRpc('/booking/get_partner', 'call', {
                        'partner_id': logged_partner_id
                    }).then(function (result) {
                        var partner = JSON.parse(result);
                        name_input.val(partner.name);
                        email_input.val(partner.email);
                        phone_input.val(partner.phone);
                        street_input.val(partner.street);
                        street2_input.val(partner.street2 || "");
                        zip_input.val(partner.zip);
                        city_input.val(partner.city);

                        address_selector.val(logged_partner_id);

                        sessionStorage.setItem('of_booking_partner_id', logged_partner_id);
                    }).fail(function() {
                        window.location.href = "/booking/error";
                    });
                }

                slots_div.hide();
                no_slot_div.hide();
            }
            else {
                service_selector.parent().addClass('has-error');
            }
        });

        contract_selector.on('change', function (event) {
            var contract_id = contract_selector.find(":selected").val();
            if (isValid(contract_id)) {
                sessionStorage.setItem('of_booking_contract_id', contract_id);
                session_contract_id = contract_id;

                contract_selector.parent().removeClass('has-error');
                contract_panel.find('.panel-collapse').collapse('hide');

                address_panel.show();
                address_panel.find('.panel-collapse').collapse('show');

                ajax.jsonRpc('/booking/get_partner', 'call', {
                    'partner_id': logged_partner_id,
                    'contract_id': session_contract_id,
                }).then(function (result) {
                    var partner = JSON.parse(result);
                    name_input.val(partner.name);
                    email_input.val(partner.email);
                    phone_input.val(partner.phone);
                    street_input.val(partner.street);
                    street2_input.val(partner.street2 || "");
                    zip_input.val(partner.zip);
                    city_input.val(partner.city);

                    sessionStorage.setItem('of_booking_partner_id', partner.id);
                }).fail(function() {
                    window.location.href = "/booking/error";
                });

                slots_div.hide();
                no_slot_div.hide();
            }
            else {
                contract_selector.parent().addClass('has-error');
            }
        });

        address_selector.on('change', function (event) {
            var address_id = address_selector.find(":selected").val();
            if (isValid(address_id)) {
                ajax.jsonRpc('/booking/get_partner', 'call', {
                    'partner_id': address_id
                }).then(function (result) {
                    var partner = JSON.parse(result);
                    name_input.val(partner.name);
                    email_input.val(partner.email);
                    phone_input.val(partner.phone);
                    street_input.val(partner.street);
                    street2_input.val(partner.street2 || "");
                    zip_input.val(partner.zip);
                    city_input.val(partner.city);

                    sessionStorage.setItem('of_booking_partner_id', address_id);
                }).fail(function() {
                    window.location.href = "/booking/error";
                });
            }
        });

        $('#new_address').on('click', function (event) {
            address_selector.val("");
            name_input.val("");
            email_input.val("");
            phone_input.val("");
            street_input.val("");
            street2_input.val("");
            zip_input.val("");
            city_input.val("");
            sessionStorage.removeItem('of_booking_partner_id');
        });

        zip_id_input.autocomplete({
            close: function(event, ui) {
                var zip_name = this.value;
                ajax.jsonRpc('/booking/get_better_zip', 'call', {
                    'zip_name': zip_name
                }).then(function (result) {
                    if (result) {
                        var zip = JSON.parse(result);
                        zip_input.val(zip.name);
                        city_input.val(zip.city);
                    }
                }).fail(function() {
                    window.location.href = "/booking/error";
                });
            }
        });

        $('#address_submit').on('click', function (event) {
            var session_partner_id = sessionStorage.getItem('of_booking_partner_id');

            var name = name_input.val();
            var name_ok = false;
            var email = email_input.val();
            var email_ok = false;
            var phone = phone_input.val();
            var phone_ok = false;
            var street = street_input.val();
            var street_ok = false;
            var street2 = street2_input.val();
            var zip = zip_input.val();
            var zip_ok = false;
            var city = city_input.val();
            var city_ok = false;

            if (name != null && name != undefined && name != "") {
                name_ok = true;
                name_input.parent().removeClass('has-error');
            }
            else {
                name_input.parent().addClass('has-error');
            }

            if (email != null && email != undefined && email != "" && email.match(/^([\w-\.]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([\w-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?)$/)) {
                email_ok = true;
                email_input.parent().removeClass('has-error');
            }
            else {
                email_input.parent().addClass('has-error');
            }

            if (phone != null && phone != undefined && phone != "") {
                phone_ok = true;
                phone_input.parent().removeClass('has-error');
            }
            else {
                phone_input.parent().addClass('has-error');
            }

            if (street != null && street != undefined && street != "") {
                street_ok = true;
                street_input.parent().removeClass('has-error');
            }
            else {
                street_input.parent().addClass('has-error');
            }

            if (zip != null && zip != undefined && zip != "") {
                zip_ok = true;
                zip_input.parent().removeClass('has-error');
            }
            else {
                zip_input.parent().addClass('has-error');
            }

            if (city != null && city != undefined && city != "") {
                city_ok = true;
                city_input.parent().removeClass('has-error');
            }
            else {
                city_input.parent().addClass('has-error');
            }

            if (name_ok && email_ok && phone_ok && street_ok && zip_ok && city_ok) {
                // Show spinner popup
                $(".container").addClass('show-popup');
                popup_text.html("Un instant svp, nous recherchons le meilleur créneau pour votre demande.");

                ajax.jsonRpc('/booking/create_update_partner', 'call', {
                    'partner_id': session_partner_id,
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'street': street,
                    'street2': street2,
                    'zip': zip,
                    'city': city
                }).then(function (partner_id) {
                    sessionStorage.setItem('of_booking_partner_id', partner_id);
                    if ($("select#address_id option[value='" + partner_id + "']").length == 0) {
                        address_selector.append($('<option>', {value: partner_id, text: zip + " - " + city}));
                        address_selector.val(partner_id);
                    }
                    address_panel.find('.panel-collapse').collapse('hide');
                    slot_panel.show();
                    slot_panel.find('.panel-collapse').collapse('show');
                    slot_panel[0].scrollIntoView();

                    from_date_input.change();
                }).fail(function() {
                    window.location.href = "/booking/error";
                });
            }
        });

        from_date_input.on('change', function (event) {
            if (!$(".container").hasClass('show-popup')) {
                // Show spinner popup
                $(".container").addClass('show-popup');
                popup_text.html("Un instant svp, nous recherchons le meilleur créneau pour votre demande.");
            }

            var from_date = from_date_input.val();
            sessionStorage.setItem('of_booking_from_date', from_date);
            session_from_date = from_date;

            session_partner_id = sessionStorage.getItem('of_booking_partner_id');

            ajax.jsonRpc('/booking/search_slots', 'call', {
                'service_id': session_service_id,
                'contract_id': session_contract_id,
                'partner_id': session_partner_id,
                'from_date': session_from_date,
            }).then(function (result) {
                booking_slots_div.html("");
                $('#search_more_submit').show();
                $('#slot_submit').show();

                var slots = result[0];
                var search_more = result[1];
                var last_day = "";
                var last_desc = "";

                for (var i = 0; i < slots.length; i++) {
                    var slot = slots[i];
                    var $slot_div = $(QWeb.render("of_website_planning_booking_v2.slot_kanban", {'title': slot.name, 'extra_info': slot.description, 'slot_id': slot.id}));
                    if (slot.description == "Matin") {
                        if (last_desc == "Matin") {
                            var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                            $unavailable_slot_div.addClass("pull-right");
                            booking_slots_div.append($unavailable_slot_div);
                        }
                        booking_slots_div.append('<div class="clearfix"/>');
                        $slot_div.addClass("pull-left");
                    }
                    else {
                        if (slot.name !== last_day) {
                            if (last_desc == "Matin") {
                                var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                                $unavailable_slot_div.addClass("pull-right");
                                booking_slots_div.append($unavailable_slot_div);
                            }
                            booking_slots_div.append('<div class="clearfix"/>');
                            var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                            $unavailable_slot_div.addClass("pull-left");
                            booking_slots_div.append($unavailable_slot_div);
                        }
                        $slot_div.addClass("pull-right");
                    }
                    $slot_div.on("click", onClickSlot);
                    booking_slots_div.append($slot_div);
                    if (slot.description === "Après-midi") {
                        booking_slots_div.append('<div class="clearfix"/>');
                    }
                    last_day = slot.name;
                    last_desc = slot.description;
                }

                if (last_desc == "Matin") {
                    var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                    $unavailable_slot_div.addClass("pull-right");
                    booking_slots_div.append($unavailable_slot_div);
                }

                if (search_more == 0) {
                    $('#search_more_submit').hide();
                }

                if (slots.length == 0) {
                    slots_div.hide();
                    no_slot_div.show();
                }
                else {
                    slots_div.show();
                    no_slot_div.hide();
                }

                // Hide spinner popup
                $(".container").removeClass('show-popup');
            }).fail(function() {
                window.location.href = "/booking/error";
            });
        });

        $('#search_more_submit').on('click', function (event) {
            // Show spinner popup
            $(".container").addClass('show-popup');
            popup_text.html("Un instant svp, nous recherchons des créneaux supplémentaires.");

            ajax.jsonRpc('/booking/search_slots', 'call', {
                'service_id': session_service_id,
                'contract_id': session_contract_id,
                'partner_id': session_partner_id,
                'from_date': session_from_date,
                'search_more': 1,
            }).then(function (result) {
                booking_slots_div.html("");

                var slots = result[0];
                var search_more = result[1];
                var last_day = "";
                var last_desc = "";

                for (var i = 0; i < slots.length; i++) {
                    var slot = slots[i];
                    var $slot_div = $(QWeb.render("of_website_planning_booking_v2.slot_kanban", {'title': slot.name, 'extra_info': slot.description, 'slot_id': slot.id}));
                    if (slot.description == "Matin") {
                        if (last_desc == "Matin") {
                            var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                            $unavailable_slot_div.addClass("pull-right");
                            booking_slots_div.append($unavailable_slot_div);
                        }
                        booking_slots_div.append('<div class="clearfix"/>');
                        $slot_div.addClass("pull-left");
                    }
                    else {
                        if (slot.name !== last_day) {
                            if (last_desc == "Matin") {
                                var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                                $unavailable_slot_div.addClass("pull-right");
                                booking_slots_div.append($unavailable_slot_div);
                            }
                            booking_slots_div.append('<div class="clearfix"/>');
                            var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                            $unavailable_slot_div.addClass("pull-left");
                            booking_slots_div.append($unavailable_slot_div);
                        }
                        $slot_div.addClass("pull-right");
                    }
                    $slot_div.on("click", onClickSlot);
                    booking_slots_div.append($slot_div);
                    if (slot.description === "Après-midi") {
                        booking_slots_div.append('<div class="clearfix"/>');
                    }
                    last_day = slot.name;
                    last_desc = slot.description;
                }

                if (last_desc == "Matin") {
                    var $unavailable_slot_div = $(QWeb.render("of_website_planning_booking_v2.unavailable_slot_kanban"));
                    $unavailable_slot_div.addClass("pull-right");
                    booking_slots_div.append($unavailable_slot_div);
                }

                if (search_more == 0) {
                    $('#search_more_submit').hide();
                }

                // Hide spinner popup
                $(".container").removeClass('show-popup');
            }).fail(function() {
                window.location.href = "/booking/error";
            });
        });

        $('#slot_submit').on('click', function (event) {
            var selected_slot = booking_slots_div.find('.panel.of-border-primary');
            var selected_slot_id = selected_slot.find('input#slot_id').val();

            if (isValid(selected_slot_id)) {
                slot_error.hide();

                website.form('/booking/confirm', 'POST', {
                    'csrf_token': core.csrf_token,
                    'intervention_id': intervention_id,
                    'service_id': session_service_id,
                    'contract_id': session_contract_id,
                    'partner_id': session_partner_id,
                    'slot_id': selected_slot_id,
                });
            }
            else {
                slot_error.show();
            }
        });

        var onClickSlot = function (event) {
            slot_error.hide();

            var old_slot = booking_slots_div.find('.panel.of-border-primary');
            old_slot.addClass('of_js_slot_change');
            old_slot.removeClass('of-border-primary');

            var new_slot = $(this).find('.panel');
            new_slot.find('.btn-ship').toggle();
            new_slot.removeClass('of_js_slot_change');
            new_slot.addClass('of-border-primary');
        };

    });
});
