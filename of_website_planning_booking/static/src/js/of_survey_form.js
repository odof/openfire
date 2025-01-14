/* eslint complexity:0 */

odoo.define("of_website_planning_booking.of_survey_form", function (require) {
    "use strict";

    const core = require("web.core");
    const wUtils = require("website.utils");
    const OFSurveyFormWidget = require("of_survey.form");
    const {getCookie, setCookie, deleteCookie} = require("web.utils.cookies");

    /*
        Surcharge du widget questionnaire pour être intégré dans la prise de RDV en ligne.
        Méthodes surchargées :_submitForm, _nextScreen, _onNextScreenDone, _prepareSubmitValues
        Les parties modifiées sont précédées des mots clés "Surcharge Booking".
     */
    OFSurveyFormWidget.include({
        /**
         * This function will send a json rpc call to the server to
         * - start the survey (if we are on start screen)
         * - submit the answers of the current page
         * Before submitting the answers, they are first validated to avoid latency from the server
         * and allow a fade out/fade in transition of the next question.
         *
         * @param {Array} [options]
         * @param {Integer} [options.previousPageId] navigates to page id
         * @param {Boolean} [options.skipValidation] skips JS validation
         * @param {Boolean} [options.initTime] will force the re-init of the timer after next
         *   screen transition
         * @param {Boolean} [options.isFinish] fades out breadcrumb and timer
         * @private
         */
        _submitForm: async function (options) {
            var self = this;
            var params = {};
            if (options.previousPageId) {
                params.previous_page_id = options.previousPageId;
            }
            var route = "/of_survey/submit";
            if (this.options && this.options.isStartScreen) {
                route = "/of_survey/begin";
                // Hide survey title in 'page_per_question' layout: it takes too much space
                if (this.options.questionsLayout === "page_per_question") {
                    this.$(".o_survey_main_title").fadeOut(400);
                }
            } else {
                var $form = this.$("form");
                var formData = new FormData($form[0]);
                if (!options.skipValidation) {
                    // Validation pre submit
                    var valid = await this._validateForm($form, formData);
                    if (!valid) {
                        return;
                    }
                }
                this._prepareSubmitValues(formData, params);
            }

            // Prevent user from submitting more times using enter key
            this.preventEnterSubmit = true;

            if (this.options.sessionInProgress) {
                // Reset the fadeInOutDelay when attendee is submitting form
                this.fadeInOutDelay = 400;
                // Prevent user from clicking on matrix options when form is submitted
                this.readonly = true;
            }

            // On ajoute dans params les images
            params.images = this.images;

            var submitPromise = self._rpc({
                route: _.str.sprintf(
                    "%s/%s/%s",
                    route,
                    self.options.surveyToken,
                    self.options.answerToken
                ),
                params: params,
            });

            // Surcharge Booking - Ajout des params dans options pour utilisation dans la fonction _onNextScreenDone
            options.params = params;

            this._nextScreen(submitPromise, options);
        },

        /**
         * Will fade out / fade in the next screen based on passed promise and options.
         *
         * @param {Promise} nextScreenPromise
         * @param {Object} options see '_submitForm' for details
         */
        _nextScreen: function (nextScreenPromise, options) {
            var self = this;

            var resolveFadeOut;
            var fadeOutPromise = new Promise(function (resolve, reject) {
                resolveFadeOut = resolve;
            });

            var selectorsToFadeout = [".o_survey_form_content"];
            if (options.isFinish) {
                selectorsToFadeout.push(".breadcrumb", ".o_survey_timer");
                deleteCookie("survey_" + self.options.surveyToken);
            }
            self.$(selectorsToFadeout.join(",")).fadeOut(
                this.fadeInOutDelay,
                function () {
                    resolveFadeOut();
                }
            );
            // Background management - Fade in / out on each transition
            if (this.options.refreshBackground) {
                $("div.o_survey_background").addClass(
                    "o_survey_background_transition"
                );
            }

            var nextScreenWithBackgroundPromise = nextScreenPromise.then(function (
                result
            ) {
                self.nextScreenResult = result;
                // Surcharge Booking - Replie la partie questionnaire lors de la soumission du formulaire
                if (result && result.booking_confirm === 1) {
                    self.$("div#survey_card").find(".collapse").collapse("hide");
                }
                // Once we have the next question, wait for the preload of the background
                if (self.options.refreshBackground && result.background_image_url) {
                    return self._preloadBackground(result.background_image_url);
                }
                    return Promise.resolve();

            });

            // Wait for the fade out and the preload of the next background. The next question have already been fetched.
            Promise.all([fadeOutPromise, nextScreenWithBackgroundPromise]).then(
                function () {
                    return self._onNextScreenDone(options);
                }
            );
        },

        /**
         * Handle server side validation and display eventual error messages.
         *
         * @param {Object} options see '_submitForm' for details
         */
        _onNextScreenDone: function (options) {
            var self = this;
            var result = this.nextScreenResult;

            if (!(options && options.isFinish) && !this.options.sessionInProgress) {
                this.preventEnterSubmit = false;
            }

            // Surcharge Booking - Soumission du formulaire de prise de RDV en ligne
            if (result && result.booking_confirm === 1) {
                return wUtils.sendRequest("/booking/confirm", options.params);
            } else if (result && !result.error) {
                this.$(".o_survey_form_content").empty();
                this.$(".o_survey_form_content").html(result.survey_content);

                if (result.survey_progress && this.$surveyProgress.length !== 0) {
                    this.$surveyProgress.html(result.survey_progress);
                } else if (options.isFinish && this.$surveyProgress.length !== 0) {
                    this.$surveyProgress.remove();
                }

                if (
                    result.survey_navigation &&
                    this.$surveyNavigation.length !== 0
                ) {
                    this.$surveyNavigation.html(result.survey_navigation);
                    this.$surveyNavigation
                        .find(".o_survey_navigation_submit")
                        .on("click", self._onSubmit.bind(self));
                }

                // Hide timer if end screen (if page_per_question in case of conditional questions)
                if (
                    self.options.questionsLayout === "page_per_question" &&
                    this.$(".o_survey_finished").length > 0
                ) {
                    options.isFinish = true;
                }

                this.$("div.o_survey_form_date").each(function () {
                    self._initDateTimePicker($(this));
                });

                this.$(".o_survey_pdf_container").each(function () {
                    const widgetPDF = new publicWidget.registry.OFSurveyFormPDFWidget(
                        this,
                        {
                            question_id: $(this).attr("id"),
                        }
                    );
                    widgetPDF.appendTo($(this));
                    self.form_pdf.push(widgetPDF);
                });

                if (this.options.isStartScreen || (options && options.initTimer)) {
                    this.options.isStartScreen = false;
                } else if (this.options.sessionInProgress && this.surveyTimerWidget) {
                        this.surveyTimerWidget.destroy();
                    }
                if (options && options.isFinish) {
                    this._initResultWidget();
                    if (this.OFSurveyBreadcrumbWidget) {
                        this.$(".o_survey_breadcrumb_container").addClass("d-none");
                        this.OFSurveyBreadcrumbWidget.destroy();
                    }
                    if (this.surveyTimerWidget) {
                        this.surveyTimerWidget.destroy();
                    }
                } else {
                    this._updateBreadcrumb();
                }
                self._initChoiceItems();
                self._initTextArea();
                self._showImages();

                if (
                    this.options.sessionInProgress &&
                    this.$(".o_survey_form_content_data").data("isPageDescription")
                ) {
                    // Prevent enter submit if we're on a page description (there is nothing to submit)
                    this.preventEnterSubmit = true;
                }
                // Background management - reset background overlay opacity to 0.7 to discover next background.
                if (this.options.refreshBackground) {
                    $("div.o_survey_background").css(
                        "background-image",
                        "url(" + result.background_image_url + ")"
                    );
                    $("div.o_survey_background").removeClass(
                        "o_survey_background_transition"
                    );
                }
                this.$(".o_survey_form_content").fadeIn(this.fadeInOutDelay);
                // Surcharge Booking - Modification du scroll automatique en haut de page lors du changement de page
                // $("html, body").animate({ scrollTop: 0 }, this.fadeInOutDelay);
                $("div#survey_card")[0].scrollIntoView();

                this.$('button[type="submit"]').removeClass("disabled");

                self._focusOnFirstInput();
            } else if (result && result.fields && result.error === "validation") {
                this.$(".o_survey_form_content").fadeIn(0);
                this._showErrors(result.fields);
            } else {
                var $errorTarget = this.$(".o_survey_error");
                $errorTarget.removeClass("d-none");
                this._scrollToError($errorTarget);
            }

            // Ici, on va vérifier chaque input pour voir s'il est déjà sélectionné ou pas quand on affiche plusieurs
            // questions sur la même page
            // Soit parce qu'il est une valeur par défaut, soit parce que nous sommes dans une modifications
            // d'un questionnaire. Cela va permettre d'afficher les questions conditionnelles de ces réponses
            if (self.options.questionsLayout != 'page_per_question') {
                self._showConditionalQuestions();
            };

            const show_end = $(".show_end").attr("data-show");
            const record_id = $(".show_end").attr("res-id");
            const model = $(".show_end").attr("res-model");
            const action_id = $(".show_end").attr("action-id");
            const survey_id = $(".show_end").attr("survey-id");
            const menu_id = $(".show_end").attr("menu-id");
            if (show_end == "no") {
                if (record_id && model && action_id) {
                    window.location =
                        "/web/#id=" +
                        record_id +
                        "&model=" +
                        model +
                        "&view_type=form&action=" +
                        action_id +
                        "&menu_id=" +
                        menu_id;
                } else {
                    window.location =
                        "/web/#id=" +
                        survey_id +
                        "&model=of.survey.survey&view_type=form";
                }
            }
        },
        _prepareSubmitValues: function (formData, params) {
            var self = this;
            formData.forEach(function (value, key) {
                // Surcharge Booking - Prise en compte des paramètres POST propre à la prise de RDV en ligne
                switch (key) {
                    case "csrf_token":
                    case "token":
                    case "page_id":
                    case "question_id":
                    case "from_planning_booking":
                    case "service_id":
                    case "contract_id":
                    case "partner_id":
                    case "slot_id":
                        params[key] = value;
                        break;
                }
            });

            // Get all question answers by question type
            this.$("[data-question-type]").each(function () {
                switch ($(this).data("questionType")) {
                    case "text_box":
                    case "char_box":
                    case "numerical_box":
                        params[this.name] = this.value;
                        break;
                    case "date":
                        params = self._prepareSubmitDates(
                            params,
                            this.name,
                            this.value,
                            false
                        );
                        break;
                    case "datetime":
                        params = self._prepareSubmitDates(
                            params,
                            this.name,
                            this.value,
                            true
                        );
                        break;
                    case "multi_image":
                        params[this.name] = [
                            $(this).data("oe-data"),
                            $(this).data("oe-file_name"),
                        ];
                    case "simple_choice_radio":
                    case "multiple_choice":
                        params = self._prepareSubmitChoices(
                            params,
                            $(this),
                            $(this).data("name")
                        );
                        break;
                    case "matrix":
                        params = self._prepareSubmitAnswersMatrix(params, $(this));
                        break;
                    case "form":
                        params[this.name] = $(this).data("oe-data");
                        break;
                }
            });
        },
    });
});
