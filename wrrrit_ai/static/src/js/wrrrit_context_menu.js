odoo.define('wrrrit_ai.context_menu', function(require) {
    "use strict";


    var core = require('web.core');
    var Widget = require('web.Widget');

    var _t = core._t;
    console.log("Context Menu Loaded detected!");

    var CustomContextMenu = Widget.extend({
        start: function() {
            this._super.apply(this, arguments);
            $(document).on('contextmenu', this._onRightClick.bind(this));
        },
        _onRightClick: function(event) {
            // Check if the right-clicked element is a text area or input field
            var targetElement = event.target;
            if (targetElement.tagName.toLowerCase() === 'textarea' || targetElement.tagName.toLowerCase() === 'input') {
                // If it's a text area or input field, do not interfere, let the default context menu appear
                return;
            }
            // Get current URL and check if it's contains the module name
            var currentUrl = window.location.href;
            var isWrrritAi = currentUrl.includes('wrrrit.ai.voice_record');
            if (!isWrrritAi) {
                // If the current URL does not contain the module name, do not interfere, let the default context menu appear
                return;
            }

            // Prevent the default context menu from appearing
            event.preventDefault();
            console.log("Right-click detected!");
             $('.custom-context-menu').remove();
            // Select all elements with the 'context-btn' class
            var buttons = $('.context-btn');

            // Define the available actions
            var actions = [];

            // Populate the actions array with the buttons
            buttons.each(function(index, button) {
                var $button = $(button);
                var contextMenuAttribute = $button.data('context-menu');

                if (contextMenuAttribute === 'include') {
                    actions.push({
                        name: $button.attr('name'), // Use the button's name attribute as the action name
                        label: $button.text(), // Use the button's text as the action label
                        content: $button.html(), // Use the button's content as the action content
                    });
                }
            });

            // Create the context menu element
            const $menu = $('<div>', {
                class: 'custom-context-menu',
                style: 'position: absolute; z-index: 9999; background-color: white; border: 1px solid black;'
            });

            const $bodyMenu = $('<ul>', {
                class: 'custom-context-menu-body',
            });

            // Add the title "Advanced Actions" to the menu
            $('<li>', {
                class: 'custom-context-menu-title', // Add a custom CSS class for the title
                text: 'Advanced Actions'
            }).appendTo($bodyMenu);

            // Populate the menu with the actions
            _.each(actions, function(action) {
                $('<li>', {
                    class: 'custom-context-menu-item', // Add a custom CSS class for menu items
                    //text: action.label
                    html: action.content
                }).on('click', function() {
                    console.log("Context menu item clicked:", action.name);

                    // Find the corresponding button and trigger a click event
                    var correspondingButton = buttons.filter('[name="' + action.name + '"]');
                    correspondingButton.click();

                }.bind(this)).appendTo($bodyMenu);
            }.bind(this));

            // Position the menu
            $menu.css({top: event.pageY, left: event.pageX});

            $bodyMenu.appendTo($menu);

            $('body').append($menu);
            console.log("Context menu displayed.");

            // Event listener to close the context menu
            $(document).one('click', function() {
                console.log("Document clicked. Removing context menu.");
                $menu.remove();
            });
        }
    });

    core.bus.on('web_client_ready', null, function() {
        new CustomContextMenu().appendTo($('body'));
    });

});
