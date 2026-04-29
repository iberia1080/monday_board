from odoo import http
from odoo.http import request


class MondayBoardGridController(http.Controller):
    @http.route("/monday_board/grid_data/<int:board_id>", type="json", auth="user")
    def grid_data(self, board_id):
        board = request.env["monday.board"].browse(board_id)
        board.check_access("read")
        return board.get_grid_payload()

    @http.route("/monday_board/update_cell", type="json", auth="user")
    def update_cell(self, board_id, row_id, column_code, value=None, tag_ids=None):
        board = request.env["monday.board"].browse(board_id)
        board.check_access("read")
        row = request.env["monday.board.row"].browse(row_id)
        row.check_access("write")
        board.update_grid_cell(row, column_code, value=value, tag_ids=tag_ids or [])
        return board.get_grid_payload()
