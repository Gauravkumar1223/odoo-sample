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
            event.preventDefault();
            console.log("Right-click detected!");

            // Define the available actions
            var actions = [
                {name: 'action_1', label: 'Action 1'},
                {name: 'action_2', label: 'Action 2'},
                {name: 'action_3', label: 'Action 3'}
            ];

            // Create the context menu element
            var $menu = $('<ul>', {
                class: 'custom-context-menu',
                style: 'position: absolute; z-index: 9999; background-color: white; border: 1px solid black;'
            });

            // Populate the menu with the actions
            _.each(actions, function(action) {
                $('<li>').text(action.label).on('click', function() {
                    console.log("Context menu item clicked:", action.name);
                    // Add any specific logic for each action click here
                }).appendTo($menu);
            });

            // Position the menu
            $menu.css({top: event.pageY, left: event.pageX});

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
