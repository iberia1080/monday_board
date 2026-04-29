{
    "name": "Monday Style Boards",
    "summary": "Custom boards in Odoo 19 with Monday-style data capture",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "OpenAI Codex",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/monday_board_groups.xml",
        "security/ir.model.access.csv",
        "views/monday_board_views.xml",
        "views/monday_board_column_views.xml",
        "views/monday_board_row_views.xml",
        "wizard/monday_import_wizard_views.xml",
        "views/monday_board_menus.xml",
        "views/monday_board_grid_action.xml",
        "data/cash_balance_template.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "monday_board/static/src/scss/monday_board_grid.scss",
            "monday_board/static/src/xml/monday_board_grid.xml",
            "monday_board/static/src/js/monday_board_grid.js",
        ],
    },
    "application": True,
    "installable": True,
}
