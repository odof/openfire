odoo.define('of_website_planning_booking_v2.of_booking', function (require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var website = require('website.website');
    var QWeb = core.qweb;

    if(!$('.of_booking').length) {
        return $.Deferred().reject("DOM doesn't contain '.of_booking'");
    }

    $('.of_booking').each(function () {
        var of_booking = this;
        var service_panel = $('div#service_panel', of_booking);
        var address_panel = $('div#address_panel', of_booking);
        var slot_panel = $('div#slot_panel', of_booking);
        var slots_div = $('div#slots_div', of_booking);
        var no_slot_div = $('div#no_slot_div', of_booking);
        var booking_slots_div = $('div#of_booking_slots', of_booking);
        var slot_error = $('div#slot_error', of_booking);

        var popup_text = $("span#popup-text");

        var service_selector = $('select#service_id', of_booking);

        var name_input = $('input#name', of_booking);
        var email_input = $('input#email', of_booking);
        var phone_input = $('input#phone', of_booking);
        var street_input = $('input#street', of_booking);
        var street2_input = $('input#street2', of_booking);
        var zip_input = $('input#zip', of_booking);
        var city_input = $('input#city', of_booking);

        var from_date_input = $('input#from_date', of_booking);

        ajax.loadXML('/of_website_planning_booking_v2/static/src/xml/of_booking_slot_kanban.xml', QWeb);

        // Session info
        var session_service_id = sessionStorage.getItem('of_booking_service_id');
        var session_partner_id = sessionStorage.getItem('of_booking_partner_id');
        var session_from_date = sessionStorage.getItem('of_booking_from_date');

        if (session_service_id != null && session_service_id != undefined && session_service_id != "" && !Number.isNaN(session_service_id)) {
            service_selector.val(session_service_id)
            service_panel.find('.panel-collapse').collapse('hide');
            address_panel.show();
        }
        else {
            service_panel.find('.panel-collapse').collapse('show');
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

        if (session_partner_id != null && session_partner_id != undefined && session_partner_id != "" && !Number.isNaN(session_partner_id)) {
            ajax.jsonRpc('/booking/get_partner', 'call', {
                'partner_id': session_partner_id
            }).then(function (result) {
                var partner = JSON.parse(result);
                name_input.val(partner.name);
                email_input.val(partner.email);
                phone_input.val(partner.phone);
                street_input.val(partner.street);
                street2_input.val(partner.street2);
                zip_input.val(partner.zip);
                city_input.val(partner.city);

                slot_panel.show();
                slot_panel.find('.panel-collapse').collapse('show');

                from_date_input.change();
            });
        }
        else {
            address_panel.find('.panel-collapse').collapse('show');
        }


        service_selector.on('change', function (event) {
            var service_id = service_selector.find(":selected").val();
            if (service_id != null && service_id != undefined && service_id != "" && !Number.isNaN(service_id)) {
                sessionStorage.setItem('of_booking_service_id', service_id);
                session_service_id = service_id;

                service_selector.parent().removeClass('has-error');
                service_panel.find('.panel-collapse').collapse('hide');

                address_panel.show();

                if (session_partner_id == null || session_partner_id == undefined || session_partner_id == "" || Number.isNaN(session_partner_id)) {
                    address_panel.find('.panel-collapse').collapse('show');
                }

                slots_div.hide();
                no_slot_div.hide();
            }
            else {
                service_selector.parent().addClass('has-error');
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
                    address_panel.find('.panel-collapse').collapse('hide');
                    slot_panel.show();
                    slot_panel.find('.panel-collapse').collapse('show');

                    from_date_input.change();
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
                'partner_id': session_partner_id,
                'from_date': session_from_date,
            }).then(function (result) {
                booking_slots_div.html("");
                $('#search_more_submit').show();
                $('#slot_submit').show();

                var slots = result[0];
                var search_more = result[1];
                var last_day = "";

                for (var i = 0; i < slots.length; i++) {
                    var slot = slots[i];
                    var $slot_div = $(QWeb.render("of_website_planning_booking_v2.slot_kanban", {'title': slot.name, 'extra_info': slot.description, 'slot_id': slot.id}));
                    if (slot.description === "Matin") {
                        booking_slots_div.append('<div class="clearfix"/>');
                        $slot_div.addClass("pull-left");
                    }
                    else {
                        if (i > 0 && slot.name !== last_day) {
                            booking_slots_div.append('<div class="clearfix"/>');
                        }
                        $slot_div.addClass("pull-right");
                    }
                    $slot_div.on("click", onClickSlot);
                    booking_slots_div.append($slot_div);
                    if (slot.description === "Après-midi") {
                        booking_slots_div.append('<div class="clearfix"/>');
                    }
                    last_day = slot.name;
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
            });
        });

        $('#search_more_submit').on('click', function (event) {
            // Show spinner popup
            $(".container").addClass('show-popup');
            popup_text.html("Un instant svp, nous recherchons des créneaux supplémentaires.");

            ajax.jsonRpc('/booking/search_slots', 'call', {
                'service_id': session_service_id,
                'partner_id': session_partner_id,
                'from_date': session_from_date,
                'search_more': 1,
            }).then(function (result) {
                booking_slots_div.html("");

                var slots = result[0];
                var search_more = result[1];
                var last_day = "";

                for (var i = 0; i < slots.length; i++) {
                    var slot = slots[i];
                    var $slot_div = $(QWeb.render("of_website_planning_booking_v2.slot_kanban", {'title': slot.name, 'extra_info': slot.description, 'slot_id': slot.id}));
                    if (slot.description === "Matin") {
                        booking_slots_div.append('<div class="clearfix"/>');
                        $slot_div.addClass("pull-left");
                    }
                    else {
                        if (i > 0 && slot.name !== last_day) {
                            booking_slots_div.append('<div class="clearfix"/>');
                        }
                        $slot_div.addClass("pull-right");
                    }
                    $slot_div.on("click", onClickSlot);
                    booking_slots_div.append($slot_div);
                    if (slot.description === "Après-midi") {
                        booking_slots_div.append('<div class="clearfix"/>');
                    }
                    last_day = slot.name;
                }

                if (search_more == 0) {
                    $('#search_more_submit').hide();
                }

                // Hide spinner popup
                $(".container").removeClass('show-popup');
            });
        });

        $('#slot_submit').on('click', function (event) {
            var selected_slot = booking_slots_div.find('.panel.of-border-primary');
            var selected_slot_id = selected_slot.find('input#slot_id').val();

            if (selected_slot_id != null && selected_slot_id != undefined && selected_slot_id != "" && !Number.isNaN(selected_slot_id)) {
                slot_error.hide();

                website.form('/booking/confirm', 'POST', {
                    'csrf_token': core.csrf_token,
                    'service_id': session_service_id,
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
