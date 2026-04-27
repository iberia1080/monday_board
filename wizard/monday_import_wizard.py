from odoo import models


class MondayImportWizard(models.TransientModel):
    _inherit = "monday.board.import.wizard"
