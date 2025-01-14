/* eslint complexity:0 */

odoo.define("of_website_planning_booking.of_booking", function (require) {
    "use strict";

    const ajax = require("web.ajax");
    const core = require("web.core");
    const publicWidget = require("web.public.widget");
    const wUtils = require("website.utils");
    const QWeb = core.qweb;
    const { _t } = core;

    publicWidget.registry.OFWebsiteBooking = publicWidget.Widget.extend({
        selector: ".of_booking_main",
        xmlDependencies: [
            "/of_website_planning_booking/static/src/xml/of_booking_slot_kanban.xml",
        ],

        _isValid: function (value) {
            return (
                value !== null &&
                value !== undefined &&
                value !== "" &&
                value !== false &&
                !isNaN(value)
            );
        },

        init: function () {
            this._super.apply(this, arguments);

            this.service_card = false;
            this.contract_card = false;
            this.address_card = false;
            this.address_select = false;
            this.slot_card = false;
            this.slots_div = false;
            this.no_slot_div = false;
            this.booking_slots_div = false;
            this.slot_error = false;
            this.survey_card = false;
            this.booking_survey_div = false;
            this.surveyFormWidget = false;
            this.popup_text = false;
            this.service_selector = false;
            this.contract_selector = false;
            this.address_selector = false;
            this.name_input = false;
            this.email_input = false;
            this.phone_input = false;
            this.street_input = false;
            this.street2_input = false;
            this.zip_input = false;
            this.city_input = false;
            this.street_div = false;
            this.street2_div = false;
            this.zip_div = false;
            this.city_div = false;
            this.from_date_input = false;
            this.logged_partner_id = false;
            this.session_mode = false;
            this.session_service_id = false;
            this.session_service_fixed = false;
            this.session_contract_id = false;
            this.session_partner_id = false;
            this.session_from_date = false;
            this.session_search_slots_result = false;
            this.session_slot_id = false;
            this.session_survey_id = false;
            this.params = false;
        },

        start() {
            const def = this._super(...arguments);

            // Initialisation de toutes les variables de la page
            const self = this;

            // Blocs principaux HTML de la page
            self.service_card = self.$("div#service_card");
            self.contract_card = self.$("div#contract_card");
            self.address_card = self.$("div#address_card");
            self.address_select = self.$("div#address_select");
            self.slot_card = self.$("div#slot_card");
            self.slots_div = self.$("div#slots_div");
            self.no_slot_div = self.$("div#no_slot_div");
            self.booking_slots_div = self.$("div#of_booking_slots");
            self.slot_error = self.$("div#slot_error");
            self.survey_card = self.$("div#survey_card");
            self.booking_survey_div = self.$("div#of_booking_survey");

            self.popup_text = $("span#popup-text");

            // Champs des formulaires et blocs associés
            self.service_selector = self.$("select#service_id");

            self.contract_selector = self.$("select#contract_id");

            self.address_selector = self.$("select#address_id");
            self.name_input = self.$("input#name");
            self.email_input = self.$("input#email");
            self.phone_input = self.$("input#phone");
            self.street_input = self.$("input#street");
            self.street2_input = self.$("input#street2");
            self.zip_input = self.$("input#zip");
            self.city_input = self.$("input#city");
            self.street_div = self.$("div#div_street");
            self.street2_div = self.$("div#div_street2");
            self.zip_div = self.$("div#div_zip");
            self.city_div = self.$("div#div_city");

            self.from_date_input = self.$("input#from_date");
            const minDate = new Date();
            minDate.setDate(minDate.getDate() + 1);
            self.from_date_input.attr("min", minDate.toISOString().slice(0, 10));

            self.logged_partner_id = self.$("input#logged_partner_id").val() || 0;

            self.params = new URLSearchParams(window.location.search);

            self.$(".collapse").on("show.bs.collapse", function () {
                $(this).siblings(".card-header").addClass("active");
            });

            self.$(".collapse").on("hide.bs.collapse", function () {
                $(this).siblings(".card-header").removeClass("active");
            });

            // Gestion des informations conservées en session
            if (self.params.get("of_return") === "1") {
                // En cas de retour arrière depuis la page de confirmation, on récupère les informations de session
                self.session_mode = sessionStorage.getItem("of_booking_mode");
                self.session_service_id = sessionStorage.getItem(
                    "of_booking_service_id"
                );
                self.session_service_fixed = sessionStorage.getItem(
                    "of_booking_service_fixed"
                );
                self.session_contract_id = sessionStorage.getItem(
                    "of_booking_contract_id"
                );
                self.session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );
                self.session_from_date = sessionStorage.getItem("of_booking_from_date");
                self.session_search_slots_result = JSON.parse(
                    sessionStorage.getItem("of_booking_search_slots_result")
                );
                self.session_slot_id = sessionStorage.getItem("of_booking_slot_id");
                self.session_survey_id = sessionStorage.getItem("of_booking_survey_id");

                const newUrl = new URL(window.location.href);
                newUrl.searchParams.delete("of_return");
                history.replaceState({}, null, newUrl.href);
            } else {
                // Arrivée sur la page, on réinitialise les informations de session.
                // Cependant, on ne retire pas du cache of_booking_partner_id pour éviter la création de doublons de partenaire
                sessionStorage.removeItem("of_booking_mode");
                sessionStorage.removeItem("of_booking_service_id");
                sessionStorage.removeItem("of_booking_service_fixed");
                sessionStorage.removeItem("of_booking_contract_id");
                self.session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );
                self.session_from_date = sessionStorage.getItem("of_booking_from_date");
                sessionStorage.removeItem("of_booking_search_slots_result");
                sessionStorage.removeItem("of_booking_slot_id");
                sessionStorage.removeItem("of_booking_survey_id");
            }

            // On détermine le mode de départ (Prestation ou Contrat)
            if (
                self.session_mode === null ||
                self.session_mode === undefined ||
                self.session_mode === false
            ) {
                if (self.logged_partner_id === 0) {
                    self.session_mode = "service";
                    self.address_select.hide();
                } else if (self.$("select#contract_id option").length > 1) {
                    self.session_mode = "contract";
                    self.address_select.hide();
                } else {
                    self.session_mode = "service";
                }
                sessionStorage.setItem("of_booking_mode", self.session_mode);
            }

            // Initialisation des différents blocs de la page en fonction des informations de session
            if (self.session_mode === "service") {
                // Initialisation du bloc Prestation
                self.contract_card.hide();
                self.service_card.show();

                if (self._isValid(self.session_service_id)) {
                    self.service_selector.val(self.session_service_id);
                    self.service_card.find(".collapse").collapse("hide");
                    self.address_card.show();
                    if (!self._isValid(self.session_partner_id)) {
                        self.address_card.find(".collapse").collapse("show");
                    }
                } else {
                    self.service_card.find(".collapse").collapse("show");
                    self.service_selector.val("");
                }

                // Initialisation du bloc Adresse et Coordonnées
                if (self.$("select#address_id option").length > 1) {
                    self.address_select.show();
                } else {
                    self.address_select.hide();
                }

                if (self.session_service_fixed === "1") {
                    self.address_card
                        .find(".card-header h2")
                        .html(_t("Contact details"));
                    self.street_div.hide();
                    self.street2_div.hide();
                    self.zip_div.hide();
                    self.city_div.hide();
                } else {
                    self.address_card
                        .find(".card-header h2")
                        .html(_t("Address and contact details"));
                    self.street_div.show();
                    self.street2_div.show();
                    self.zip_div.show();
                    self.city_div.show();
                }
            } else if (self.session_mode === "contract") {
                // Initialisation du bloc Contrat
                self.contract_card.show();
                self.service_card.hide();

                if (self._isValid(self.session_contract_id)) {
                    self.contract_selector.val(self.session_contract_id);
                    self.contract_card.find(".collapse").collapse("hide");
                    self.address_card.show();
                    if (!self._isValid(self.session_partner_id)) {
                        self.address_card.find(".collapse").collapse("show");
                    }
                } else {
                    self.contract_card.find(".collapse").collapse("show");
                    self.contract_selector.val("");
                }

                // Initialisation du bloc Adresse et Coordonnées
                self.address_select.hide();
                self.address_card
                    .find(".card-header h2")
                    .html(_t("Address and contact details"));
                self.street_div.show();
                self.street2_div.show();
                self.zip_div.show();
                self.city_div.show();
            }

            // Initialisation du champ Date
            if (
                self.session_from_date !== null &&
                self.session_from_date !== undefined &&
                self.session_from_date !== ""
            ) {
                self.from_date_input.val(self.session_from_date);
            } else {
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                const tomorrow_str = moment(tomorrow).format("YYYY-MM-DD");
                self.from_date_input.val(tomorrow_str);
            }

            // Récupération des informations du client
            if (
                self._isValid(self.session_partner_id) &&
                self._isValid(self.session_service_id || self.session_contract_id)
            ) {
                /**
                 * We don't want to display the time slot map when `session_contract_id` or `session_service_id` are
                 * `false` according to their respective session mode.
                 */
                const showSlotCard =
                    !(self.session_mode === "contract" && !self.session_contract_id) &&
                    !(self.session_mode === "service" && !self.session_service_id);

                self._fetchPartnerAndUpdateUI(self.session_partner_id, {
                    partner_id: self.session_partner_id,
                    hideAddressCard: true,
                    showSlotCard: showSlotCard,
                });

                // Initialisation du bloc Informations complémentaires
                if (self._isValid(self.session_survey_id)) {
                    self._fetchSurveyAndUpdateUI(self.session_slot_id);
                }
            }

            // Clic sur le bouton Mes contrats
            self.$("#my_contracts").on("click", function (event) {
                self.session_mode = "contract";
                sessionStorage.setItem("of_booking_mode", self.session_mode);
                sessionStorage.removeItem("of_booking_service_id");
                sessionStorage.removeItem("of_booking_service_fixed");
                self.session_service_id = false;
                self.service_selector.val("");
                self.service_card.hide();
                self.service_card.find(".collapse").collapse("hide");
                self.contract_card.show();
                self.contract_card.find(".collapse").collapse("show");
                self.address_select.hide();
                self.address_card
                    .find(".card-header h2")
                    .html(_t("Address and contact details"));
                self.street_div.show();
                self.street2_div.show();
                self.zip_div.show();
                self.city_div.show();
                self.address_card.hide();
                self.address_card.find(".collapse").collapse("hide");
                self.slot_card.hide();
                self.slot_card.find(".collapse").collapse("hide");
                sessionStorage.removeItem("of_booking_survey_id");
                self.session_survey_id = false;
                self.booking_survey_div.empty();
                self.survey_card.hide();
                self.survey_card.find(".collapse").collapse("hide");
            });

            // Clic sur le bouton Autres prestations
            self.$("#other_services").on("click", function (event) {
                self.session_mode = "service";
                sessionStorage.setItem("of_booking_mode", self.session_mode);
                sessionStorage.removeItem("of_booking_contract_id");
                self.session_contract_id = false;
                self.contract_selector.val("");
                self.service_card.show();
                self.service_card.find(".collapse").collapse("show");
                self.contract_card.hide();
                self.contract_card.find(".collapse").collapse("hide");
                if (self.$("select#address_id option").length > 1) {
                    self.address_select.show();
                } else {
                    self.address_select.hide();
                }
                self.address_card.hide();
                self.address_card.find(".collapse").collapse("hide");
                self.slot_card.hide();
                self.slot_card.find(".collapse").collapse("hide");
                sessionStorage.removeItem("of_booking_survey_id");
                self.session_survey_id = false;
                self.booking_survey_div.empty();
                self.survey_card.hide();
                self.survey_card.find(".collapse").collapse("hide");
            });

            // Sélection d'une prestation
            self.service_selector.on("change", function (event) {
                const service_id = self.service_selector.find(":selected").val();
                if (self._isValid(service_id)) {
                    const service_fixed = self.service_selector
                        .find(":selected")
                        .data("fixed");
                    const survey_id = self.service_selector
                        .find(":selected")
                        .data("surveyId");

                    sessionStorage.setItem("of_booking_service_id", service_id);
                    sessionStorage.setItem("of_booking_service_fixed", service_fixed);
                    sessionStorage.setItem("of_booking_survey_id", survey_id);
                    self.session_service_id = service_id;
                    self.session_service_fixed =
                        service_fixed && service_fixed.toString();
                    self.session_survey_id = survey_id;

                    sessionStorage.removeItem("of_booking_contract_id");

                    self.service_selector.removeClass("is-invalid");
                    self.service_card.find(".collapse").collapse("hide");

                    // Gestion des RDV fixes
                    if (self.session_service_fixed === "1") {
                        self.address_card
                            .find(".card-header h2")
                            .html(_t("Contact details"));
                        self.street_div.hide();
                        self.street2_div.hide();
                        self.zip_div.hide();
                        self.city_div.hide();
                    } else {
                        self.address_card
                            .find(".card-header h2")
                            .html(_t("Address and contact details"));
                        self.street_div.show();
                        self.street2_div.show();
                        self.zip_div.show();
                        self.city_div.show();
                    }

                    self.address_card.show();
                    self.address_card.find(".collapse").collapse("show");

                    // Récupération des informations du client
                    if (
                        !self._isValid(self.session_partner_id) &&
                        self.logged_partner_id !== 0
                    ) {
                        self._fetchPartnerAndUpdateUI(self.logged_partner_id, {
                            partner_id: self.logged_partner_id,
                        });
                    } else if (self._isValid(self.session_partner_id)) {
                        self._fetchPartnerAndUpdateUI(self.session_partner_id, {
                            partner_id: self.session_partner_id,
                        });
                    }
                    self.slots_div.hide();
                    self.no_slot_div.hide();

                    self.booking_survey_div.empty();
                    self.survey_card.hide();
                    self.survey_card.find(".collapse").collapse("hide");
                } else {
                    self.service_selector.addClass("is-invalid");
                }
            });

            // Sélection d'un contrat
            self.contract_selector.on("change", function (event) {
                const contract_id = self.contract_selector.find(":selected").val();
                if (self._isValid(contract_id)) {
                    sessionStorage.setItem("of_booking_contract_id", contract_id);
                    self.session_contract_id = contract_id;

                    sessionStorage.removeItem("of_booking_service_id");

                    self.contract_selector.removeClass("is-invalid");
                    self.contract_card.find(".collapse").collapse("hide");

                    self.address_card.show();
                    self.address_card.find(".collapse").collapse("show");

                    // Récupération des informations du client
                    self._fetchPartnerAndUpdateUI(self.logged_partner_id, {
                        partner_id: self.logged_partner_id,
                        contract_id: self.session_contract_id,
                    });

                    self.slots_div.hide();
                    self.no_slot_div.hide();

                    self.booking_survey_div.empty();
                    self.survey_card.hide();
                    self.survey_card.find(".collapse").collapse("hide");
                } else {
                    self.contract_selector.addClass("is-invalid");
                }
            });

            // Sélection d'une adresse existante
            self.address_selector.on("change", function (event) {
                const address_id = self.address_selector.find(":selected").val() || 0;
                if (self._isValid(address_id)) {
                    self._fetchPartnerAndUpdateUI(address_id, {
                        partner_id: address_id,
                    });
                }
            });

            // Clic sur le bouton Nouvelle adresse
            self.$("#new_address").on("click", function (event) {
                self._fetchPartnerAndUpdateUI(self.logged_partner_id, {
                    resetAddress: true,
                });
            });

            // Validation du formulaire Adresse et Coordonnées
            self.$("#address_submit").on("click", function (event) {
                const session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );

                // Contrôle des informations saisies
                const name = self.name_input.val();
                let name_ok = false;
                const email = self.email_input.val();
                let email_ok = false;
                const phone = self.phone_input.val();
                let phone_ok = false;
                const street = self.street_input.val();
                let street_ok = false;
                const street2 = self.street2_input.val();
                const zip = self.zip_input.val();
                let zip_ok = false;
                const city = self.city_input.val();
                let city_ok = false;

                if (name !== null && name !== undefined && name !== "") {
                    name_ok = true;
                    self.name_input.removeClass("is-invalid");
                } else {
                    self.name_input.addClass("is-invalid");
                }

                if (
                    email !== null &&
                    email !== undefined &&
                    email !== "" &&
                    email.match(
                        /^([\w-\.]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([\w-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?)$/
                    )
                ) {
                    email_ok = true;
                    self.email_input.removeClass("is-invalid");
                } else {
                    self.email_input.addClass("is-invalid");
                }

                if (phone !== null && phone !== undefined && phone !== "") {
                    phone_ok = true;
                    self.phone_input.removeClass("is-invalid");
                } else {
                    self.phone_input.addClass("is-invalid");
                }

                if (
                    self.session_service_fixed === "1" ||
                    (street !== null && street !== undefined && street !== "")
                ) {
                    street_ok = true;
                    self.street_input.removeClass("is-invalid");
                } else {
                    self.street_input.addClass("is-invalid");
                }

                if (
                    self.session_service_fixed === "1" ||
                    (zip !== null && zip !== undefined && zip !== "")
                ) {
                    zip_ok = true;
                    self.zip_input.removeClass("is-invalid");
                } else {
                    self.zip_input.addClass("is-invalid");
                }

                if (
                    self.session_service_fixed === "1" ||
                    (city !== null && city !== undefined && city !== "")
                ) {
                    city_ok = true;
                    self.city_input.removeClass("is-invalid");
                } else {
                    self.city_input.addClass("is-invalid");
                }

                if (name_ok && email_ok && phone_ok && street_ok && zip_ok && city_ok) {
                    // Show spinner popup
                    $(".container").addClass("show-popup");
                    self.popup_text.html(
                        _t(
                            "One moment please, we are looking for the best slot for your request."
                        )
                    );

                    // Création ou mise à jour du contact
                    ajax.jsonRpc("/booking/create_update_partner", "call", {
                        partner_id: session_partner_id,
                        name: name,
                        email: email,
                        phone: phone,
                        street: street,
                        street2: street2,
                        zip: zip,
                        city: city,
                    })
                        .then(function (partner_id) {
                            sessionStorage.setItem("of_booking_partner_id", partner_id);

                            // Mise à jour du sélecteur d'adresse si nécessaire
                            if (
                                self.$(
                                    `select#address_id option[value="${partner_id}"]`
                                ).length === 0
                            ) {
                                self.address_selector.append(
                                    $("<option>", {
                                        value: partner_id,
                                        text: `${zip} - ${city}`,
                                    })
                                );
                                self.address_selector.val(partner_id);
                            }
                            self.address_card.find(".collapse").collapse("hide");
                            self.slot_card.show();
                            self.slot_card.find(".collapse").collapse("show");
                            self.slot_card[0].scrollIntoView();

                            // Déclenchement de la recherche de créneaux
                            self.from_date_input.change();
                        })
                        .catch((error) => {
                            window.location.href = "/booking/error";
                        });
                }
            });

            // Modification du champ date
            self.from_date_input.on("change", function (event) {
                if (!$(".container").hasClass("show-popup")) {
                    // Show spinner popup
                    $(".container").addClass("show-popup");
                    self.popup_text.html(
                        _t(
                            "One moment please, we are looking for the best slot for your request."
                        )
                    );
                }

                const from_date = self.from_date_input.val();
                sessionStorage.setItem("of_booking_from_date", from_date);
                self.session_from_date = from_date;

                self.session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );

                self.slot_error.hide();

                // Appel de la recherche de créneaux
                self._fetchSlotAndUpdateUI();
            });

            // Clic sur le bouton Chercher plus
            $("#search_more_submit").on("click", function (event) {
                // Show spinner popup
                $(".container").addClass("show-popup");
                self.popup_text.html(
                    _t("One moment please, we are looking for additional slots.")
                );

                self.slot_error.hide();

                // Appel de la recherche de créneaux
                self._fetchSlotAndUpdateUI({ search_more: true });
            });

            // Validation du créneau sélectionné
            $("#slot_submit").on("click", function (event) {
                const selectedSlot = self.booking_slots_div.find(
                    ".card.of-border-primary"
                );
                const selectedSlotId = selectedSlot.find("input#slot_id").val();

                if (self._isValid(selectedSlotId)) {
                    sessionStorage.setItem("of_booking_slot_id", selectedSlotId);

                    self.slot_error.hide();

                    // Affichage de l'étape Informations complémentaires ou redirection vers la page de confirmation
                    if (
                        self._isValid(self.session_service_id) &&
                        self._isValid(self.session_survey_id)
                    ) {
                        self._fetchSurveyAndUpdateUI(selectedSlotId, { showSurvey: true });
                    } else {
                        // Redirection vers la page de confirmation
                        return wUtils.sendRequest("/booking/confirm", {
                            csrf_token: core.csrf_token,
                            service_id: self.session_service_id,
                            contract_id: self.session_contract_id,
                            partner_id: self.session_partner_id,
                            slot_id: selectedSlotId,
                        });
                    }
                } else {
                    self.slot_error.show();
                }
            });

            return def;
        },

        /**
         * Updates fields address of the UI.
         * Thats also and store values in session storage and make some cards hidden/displayed depending on options.
         *
         * @param {Object} partner
         * @param {Object} options
         */
        _updatePartnerUI: function (partner, options = {}) {
            this.name_input.val(partner.name);
            this.email_input.val(partner.email);
            this.phone_input.val(partner.phone);
            this.street_input.val(partner.street);
            this.street2_input.val(partner.street2);
            this.zip_input.val(partner.zip);
            this.city_input.val(partner.city);

            let sessionBookingPartner = false;
            if (options.contract_id) {
                sessionBookingPartner = partner.id;
            } else {
                sessionBookingPartner = options.partner_id || false;
            }

            if (options.partner_id && !options.contract_id) {
                this.address_selector.val(options.partner_id);
            }
            if (sessionBookingPartner) {
                sessionStorage.setItem("of_booking_partner_id", sessionBookingPartner);
            }

            if (options.hideAddressCard) {
                this.address_card.find(".collapse").collapse("hide");
            }

            if (options.showSlotCard) {
                this.slot_card.show();

                var self = this;

                if (self._isValid(self.session_slot_id)) {
                    self.booking_slots_div.html("");
                    const result = self.session_search_slots_result;

                    $("#search_more_submit").show();
                    $("#slot_submit").show();

                    const slots = result[0];
                    const searchMore = result[1];
                    let lastDay = "";
                    let lastDesc = "";

                    for (let i = 0; i < slots.length; i++) {
                        const slot = slots[i];
                        const $slotDiv = $(
                            QWeb.render("of_website_planning_booking.slot_kanban", {
                                title: slot.name,
                                extra_info: slot.description,
                                slot_id: slot.id,
                            })
                        );
                        if (slot.description === _t("Morning")) {
                            if (lastDesc === _t("Morning")) {
                                self.booking_slots_div.append(
                                    self._createUnavailableSlotDiv("float-end")
                                );
                            }
                            self._appendClearfix(self.booking_slots_div);
                            $slotDiv.addClass("float-start");
                        } else {
                            if (slot.name !== lastDay) {
                                if (lastDesc === _t("Morning")) {
                                    self.booking_slots_div.append(
                                        self._createUnavailableSlotDiv("float-end")
                                    );
                                }
                                self._appendClearfix(self.booking_slots_div);
                                self.booking_slots_div.append(
                                    self._createUnavailableSlotDiv("float-start")
                                );
                            }
                            $slotDiv.addClass("float-end");
                        }
                        $slotDiv.on("click", self._onClickSlot);
                        self.booking_slots_div.append($slotDiv);
                        if (slot.description === _t("Afternoon")) {
                            self._appendClearfix(self.booking_slots_div);
                        }
                        lastDay = slot.name;
                        lastDesc = slot.description;
                    }

                    if (lastDesc === _t("Morning")) {
                        self.booking_slots_div.append(
                            self._createUnavailableSlotDiv("float-end")
                        );
                    }

                    if (searchMore === false) {
                        $("#search_more_submit").hide();
                    }

                    if (slots.length === 0) {
                        self.slots_div.hide();
                        self.no_slot_div.show();
                    } else {
                        self.slots_div.show();
                        self.no_slot_div.hide();
                    }

                    // Select slot
                    const selectedSlot = self.booking_slots_div
                        .find('input[value="' + self.session_slot_id + '"]')
                        .closest(".card.of_js_slot_change");
                    selectedSlot.removeClass("of_js_slot_change");
                    selectedSlot.addClass("of-border-primary");
                } else {
                    this.slot_card.find(".collapse").collapse("show");
                    this.from_date_input.change();
                }
            }
        },

        /**
         * Get Partner data from Odoo and updates UI depending on values fetched and options.
         *
         * @param {Integer} partner_id
         * @param {Objet} options
         */
        _fetchPartnerAndUpdateUI: function (partner_id, options = {}) {
            const self = this;
            const params = { partner_id };
            if (options.contract_id) {
                params.contract_id = options.contract_id;
            }

            ajax.jsonRpc("/booking/get_partner", "call", params)
                .then(function (result) {
                    const partner = JSON.parse(result);

                    self._updatePartnerUI(partner, options);

                    if (options.resetAddress) {
                        self.street_input.val("");
                        self.street2_input.val("");
                        self.zip_input.val("");
                        self.city_input.val("");
                        sessionStorage.removeItem("of_booking_partner_id");
                    }
                })
                .catch(() => {
                    window.location.href = "/booking/error";
                });
        },

        /**
         * Appends a clearfix `div` to the given container.
         * @param {Element} container
         */
        _appendClearfix: function (container) {
            container.append('<div class="clearfix"/>');
        },

        /**
         * Render unavailable slot div.
         * @param {String} floatClass
         * @returns {Element} div
         */
        _createUnavailableSlotDiv: function (floatClass) {
            const $unavailableSlotDiv = $(
                QWeb.render("of_website_planning_booking.unavailable_slot_kanban")
            );
            $unavailableSlotDiv.addClass(floatClass);
            return $unavailableSlotDiv;
        },

        /**
         * Decorate the clicked div and remove decoration from the previous one.
         * @param {Event} event
         */
        _onClickSlot: function (event) {
            $(self.slot_error).hide(); // eslint-disable-line

            const oldSlotDiv = $(self.of_booking_slots).find(".card.of-border-primary"); // eslint-disable-line
            oldSlotDiv.addClass("of_js_slot_change");
            oldSlotDiv.removeClass("of-border-primary");

            const newSlotDiv = $(this).find(".card");
            newSlotDiv.find(".btn-ship").toggle();
            newSlotDiv.removeClass("of_js_slot_change");
            newSlotDiv.addClass("of-border-primary");
        },

        /**
         * Updates Slots div of the UI.
         *
         * @param {Object} result
         * @param {Object} options
         */
        _updateSlotUI: function (result, options = {}) {
            const self = this;

            self.booking_slots_div.html("");
            $("#search_more_submit").show();
            $("#slot_submit").show();

            const slots = result[0];
            const searchMore = result[1];
            let lastDay = "";
            let lastDesc = "";

            for (let i = 0; i < slots.length; i++) {
                const slot = slots[i];
                const $slotDiv = $(
                    QWeb.render("of_website_planning_booking.slot_kanban", {
                        title: slot.name,
                        extra_info: slot.description,
                        slot_id: slot.id,
                    })
                );
                if (slot.description === _t("Morning")) {
                    if (lastDesc === _t("Morning")) {
                        self.booking_slots_div.append(
                            self._createUnavailableSlotDiv("float-end")
                        );
                    }
                    self._appendClearfix(self.booking_slots_div);
                    $slotDiv.addClass("float-start");
                } else {
                    if (slot.name !== lastDay) {
                        if (lastDesc === _t("Morning")) {
                            self.booking_slots_div.append(
                                self._createUnavailableSlotDiv("float-end")
                            );
                        }
                        self._appendClearfix(self.booking_slots_div);
                        self.booking_slots_div.append(
                            self._createUnavailableSlotDiv("float-start")
                        );
                    }
                    $slotDiv.addClass("float-end");
                }
                $slotDiv.on("click", self._onClickSlot);
                self.booking_slots_div.append($slotDiv);
                if (slot.description === _t("Afternoon")) {
                    self._appendClearfix(self.booking_slots_div);
                }
                lastDay = slot.name;
                lastDesc = slot.description;
            }

            if (lastDesc === _t("Morning")) {
                self.booking_slots_div.append(
                    self._createUnavailableSlotDiv("float-end")
                );
            }

            if (searchMore === false) {
                $("#search_more_submit").hide();
            }

            if (!options.search_more) {
                if (slots.length === 0) {
                    self.slots_div.hide();
                    self.no_slot_div.show();
                } else {
                    self.slots_div.show();
                    self.no_slot_div.hide();
                }
            }

            // Hide spinner popup
            $(".container").removeClass("show-popup");
        },

        /**
         * Get Slots data from Odoo and updates UI depending on result fetched and options.
         *
         * @param {Objet} options
         */
        _fetchSlotAndUpdateUI: function (options = {}) {
            const self = this;
            const params = {
                service_id: self.session_service_id,
                contract_id: self.session_contract_id,
                partner_id: self.session_partner_id,
                from_date: self.session_from_date,
            };
            if (options.search_more) {
                params.search_more = true;
            }

            ajax.jsonRpc("/booking/search_slots", "call", params)
                .then(function (result) {
                    sessionStorage.setItem(
                        "of_booking_search_slots_result",
                        JSON.stringify(result)
                    );

                    self._updateSlotUI(result, options);
                })
                .catch((error) => {
                    window.location.href = "/booking/error";
                });
        },

        /**
         * Updates Survey div of the UI and initialize Survey widget.
         *
         * @param {String} html
         * @param {Object} options
         */
        _updateSurveyUI: function (html, options = {}) {
            const self = this;

            self.booking_survey_div.empty();
            self.booking_survey_div.html(html);

            // Initialisation du widget Survey
            if (self.surveyFormWidget) {
                self.surveyFormWidget.destroy();
                delete self.surveyFormWidget;
            }
            self.surveyFormWidget = new publicWidget.registry.OFSurveyFormWidget(self);
            self.surveyFormWidget.attachTo(self.$(".o_survey_form"));

            self.survey_card.show();

            if (options.showSurvey) {
                self.slot_card.find(".collapse").collapse("hide");
                self.survey_card.find(".collapse").collapse("show");
                self.slot_card[0].scrollIntoView();
            }
        },

        /**
         * Get Survey data from Odoo and updates UI depending on result fetched and options.
         *
         * @param {Integer} slot_id
         */
        _fetchSurveyAndUpdateUI: function (slot_id, options = {}) {
            const self = this;
            const params = {
                csrf_token: core.csrf_token,
                service_id: self.session_service_id,
                contract_id: self.session_contract_id,
                partner_id: self.session_partner_id,
                slot_id: slot_id,
            };

            // Appel de la route initiale de gestion du questionnaire
            ajax.jsonRpc("/booking/survey", "call", params)
                .then(function (result) {
                    if ("error" in result) {
                        window.location.href = "/booking/error";
                    } else {
                        // Affichage du questionnaire
                        self._updateSurveyUI(result.html, options);
                    }
                })
                .catch((error) => {
                    window.location.href = "/booking/error";
                });
        },
    });

    publicWidget.registry.OFWebsiteBookingConfirm = publicWidget.Widget.extend({
        selector: ".of_booking_confirm",
        start() {
            const def = this._super(...arguments);

            // Modification du comportement standard du bouton arrière du navigateur web afin
            // d'appeler l'URL "/booking?of_return=1" permettant de correctement recharger les données
            window.history.pushState(null, null, window.location.href);
            window.addEventListener("popstate", () => {
                window.location.href = "/booking?of_return=1";
            });

            return def;
        },
    });
});
