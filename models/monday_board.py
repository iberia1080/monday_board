import json
from urllib import error, request

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


STATUS_COLORS = [
    ("0", "Gris"),
    ("1", "Verde"),
    ("2", "Rojo"),
    ("3", "Azul"),
    ("4", "Morado"),
    ("5", "Verde Claro"),
    ("6", "Rosa"),
    ("7", "Lila"),
    ("8", "Azul Cielo"),
    ("9", "Verde Fuerte"),
    ("10", "Rosa Claro"),
    ("11", "Azul Fuerte"),
    ("12", "Naranja"),
]


class MondayBoard(models.Model):
    _name = "monday.board"
    _description = "Monday Style Board"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    owner_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user, tracking=True
    )
    column_ids = fields.One2many("monday.board.column", "board_id", string="Columns")
    row_ids = fields.One2many("monday.board.row", "board_id", string="Rows")
    tag_ids = fields.One2many("monday.board.tag", "board_id", string="Tags")
    row_count = fields.Integer(compute="_compute_counts")
    column_count = fields.Integer(compute="_compute_counts")

    @api.depends("column_ids", "row_ids")
    def _compute_counts(self):
        for board in self:
            board.row_count = len(board.row_ids)
            board.column_count = len(board.column_ids)

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Monday Board"),
            "res_model": "monday.board.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_target_board_id": self.id},
        }

    def action_open_rows(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Board Rows"),
            "res_model": "monday.board.row",
            "view_mode": "list,form",
            "domain": [("board_id", "=", self.id)],
            "context": {"default_board_id": self.id, "search_default_board_id": self.id},
        }


class MondayBoardColumn(models.Model):
    _name = "monday.board.column"
    _description = "Monday Style Board Column"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    board_id = fields.Many2one("monday.board", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    field_type = fields.Selection(
        [
            ("text", "Text"),
            ("number", "Number"),
            ("date", "Date"),
            ("time", "Time"),
            ("user", "User"),
            ("tag", "Tag"),
            ("status", "Status"),
            ("attachment", "Attachment"),
            ("formula", "Formula"),
            ("audit", "Audit Summary"),
            ("creation", "Creation Summary"),
        ],
        required=True,
        default="text",
    )
    width = fields.Integer(default=180)
    is_currency = fields.Boolean()
    currency_symbol = fields.Char(default="$")
    status_option_ids = fields.One2many(
        "monday.board.status.option", "column_id", string="Status Options"
    )
    tag_ids = fields.One2many("monday.board.tag", "column_id", string="Available Tags")
    formula_expression = fields.Char(
        help="Python expression using column codes, for example: entrada - salida if dinero == 'Realizado' else ''"
    )
    view_group_ids = fields.Many2many(
        "res.groups",
        "monday_column_view_group_rel",
        "column_id",
        "group_id",
        string="View Groups",
    )
    edit_group_ids = fields.Many2many(
        "res.groups",
        "monday_column_edit_group_rel",
        "column_id",
        "group_id",
        string="Edit Groups",
    )
    is_visible_for_current_user = fields.Boolean(compute="_compute_current_user_access")
    is_editable_for_current_user = fields.Boolean(compute="_compute_current_user_access")

    _sql_constraints = [
        ("board_code_unique", "unique(board_id, code)", "Column code must be unique per board."),
    ]

    @api.constrains("code")
    def _check_code(self):
        for column in self:
            if not column.code:
                continue
            normalized = column.code.strip().lower()
            if not normalized.replace("_", "").isalnum():
                raise ValidationError(
                    _("Column code must use only letters, numbers, and underscores.")
                )

    @api.constrains("field_type", "formula_expression")
    def _check_formula_expression(self):
        for column in self:
            if column.field_type == "formula" and not column.formula_expression:
                raise ValidationError(_("Formula columns require a formula expression."))

    @api.depends("view_group_ids", "edit_group_ids")
    def _compute_current_user_access(self):
        user = self.env.user
        for column in self:
            column.is_visible_for_current_user = column.can_user_view(user)
            column.is_editable_for_current_user = column.can_user_edit(user)

    def can_user_view(self, user):
        self.ensure_one()
        if not self.view_group_ids:
            return True
        return bool(self.view_group_ids & user.groups_id)

    def can_user_edit(self, user):
        self.ensure_one()
        if self.field_type in ("formula", "audit", "creation"):
            return False
        if not self.edit_group_ids:
            return True
        return bool(self.edit_group_ids & user.groups_id)


class MondayBoardTag(models.Model):
    _name = "monday.board.tag"
    _description = "Monday Board Tag"
    _order = "name"

    name = fields.Char(required=True)
    color = fields.Integer(default=1)
    board_id = fields.Many2one("monday.board", required=True, ondelete="cascade")
    column_id = fields.Many2one("monday.board.column", required=True, ondelete="cascade")

    _sql_constraints = [
        ("board_column_tag_unique", "unique(column_id, name)", "Tag must be unique per column."),
    ]


class MondayBoardStatusOption(models.Model):
    _name = "monday.board.status.option"
    _description = "Monday Board Status Option"
    _order = "sequence, id"

    name = fields.Char()
    sequence = fields.Integer(default=10)
    color = fields.Selection(STATUS_COLORS, default="0", required=True)
    is_default = fields.Boolean()
    column_id = fields.Many2one("monday.board.column", required=True, ondelete="cascade")

    _sql_constraints = [
        ("column_status_name_unique", "unique(column_id, name)", "Status must be unique per column."),
    ]


class MondayBoardRow(models.Model):
    _name = "monday.board.row"
    _description = "Monday Style Board Row"
    _inherit = ["mail.thread"]
    _order = "sequence, id"

    name = fields.Char(compute="_compute_name", store=True)
    board_id = fields.Many2one("monday.board", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    cell_ids = fields.One2many("monday.board.cell", "row_id", string="Cells")
    change_log_ids = fields.One2many("monday.board.change.log", "row_id", string="Change Log")
    last_update_summary = fields.Char(compute="_compute_summaries", store=False)
    creation_summary = fields.Char(compute="_compute_summaries", store=False)
    movement_tag_ids = fields.Many2many(
        "monday.board.tag",
        "monday_row_movement_tag_rel",
        "row_id",
        "tag_id",
        compute="_compute_tag_fields",
        string="Movimiento Tags",
        store=True,
    )
    branch_tag_ids = fields.Many2many(
        "monday.board.tag",
        "monday_row_branch_tag_rel",
        "row_id",
        "tag_id",
        compute="_compute_tag_fields",
        string="Sucursal Tags",
        store=True,
    )

    @api.depends(
        "cell_ids.value_text",
        "cell_ids.value_number",
        "cell_ids.value_date",
        "cell_ids.value_status",
        "cell_ids.value_user_id",
    )
    def _compute_name(self):
        for row in self:
            concept_cell = row.cell_ids.filtered(lambda c: c.column_id.code == "concepto")[:1]
            row.name = concept_cell.value_text if concept_cell and concept_cell.value_text else _("Row %s") % row.id

    @api.depends("write_date", "write_uid", "create_date", "create_uid", "change_log_ids")
    def _compute_summaries(self):
        for row in self:
            if row.change_log_ids:
                last_log = row.change_log_ids.sorted("change_date", reverse=True)[:1]
                row.last_update_summary = _(
                    "%s por %s"
                ) % (
                    fields.Datetime.to_string(last_log.change_date),
                    last_log.user_id.name,
                )
            else:
                row.last_update_summary = ""
            row.creation_summary = _("%s por %s") % (
                fields.Datetime.to_string(row.create_date) if row.create_date else "",
                row.create_uid.name if row.create_uid else "",
            )

    @api.depends("cell_ids.tag_ids", "cell_ids.column_id.code")
    def _compute_tag_fields(self):
        for row in self:
            movement = row.cell_ids.filtered(lambda c: c.column_id.code == "movimiento")[:1]
            branch = row.cell_ids.filtered(lambda c: c.column_id.code == "sucursal")[:1]
            row.movement_tag_ids = movement.tag_ids
            row.branch_tag_ids = branch.tag_ids

    @api.model_create_multi
    def create(self, vals_list):
        rows = super().create(vals_list)
        rows._ensure_missing_cells()
        return rows

    def _ensure_missing_cells(self):
        cell_model = self.env["monday.board.cell"]
        for row in self:
            existing_columns = set(row.cell_ids.mapped("column_id").ids)
            for column in row.board_id.column_ids:
                if column.id not in existing_columns:
                    cell_model.with_context(skip_board_access_check=True).create(
                        {
                            "row_id": row.id,
                            "board_id": row.board_id.id,
                            "column_id": column.id,
                        }
                    )

    def action_open_change_log(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Historial de Cambios"),
            "res_model": "monday.board.change.log",
            "view_mode": "list,form",
            "domain": [("row_id", "=", self.id)],
            "target": "current",
        }


class MondayBoardCell(models.Model):
    _name = "monday.board.cell"
    _description = "Monday Style Board Cell"
    _order = "row_id, column_id"

    board_id = fields.Many2one("monday.board", required=True, ondelete="cascade")
    row_id = fields.Many2one("monday.board.row", required=True, ondelete="cascade")
    column_id = fields.Many2one("monday.board.column", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="board_id.currency_id", store=False)
    value_text = fields.Char()
    value_number = fields.Monetary(currency_field="currency_id")
    value_date = fields.Date()
    value_user_id = fields.Many2one("res.users")
    value_status = fields.Char()
    value_status_color = fields.Selection(STATUS_COLORS)
    tag_ids = fields.Many2many("monday.board.tag", string="Tags")
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    display_value = fields.Char(compute="_compute_display_value", store=False)
    can_edit = fields.Boolean(compute="_compute_access_flags")
    can_view = fields.Boolean(compute="_compute_access_flags")

    _sql_constraints = [
        ("board_row_column_unique", "unique(row_id, column_id)", "Only one cell per row and column."),
    ]

    @api.constrains("board_id", "row_id", "column_id")
    def _check_relations(self):
        for cell in self:
            if cell.row_id and cell.board_id and cell.row_id.board_id != cell.board_id:
                raise ValidationError(_("Row board and cell board must match."))
            if cell.column_id and cell.board_id and cell.column_id.board_id != cell.board_id:
                raise ValidationError(_("Column board and cell board must match."))

    @api.depends(
        "column_id",
        "value_text",
        "value_number",
        "value_date",
        "value_status",
        "value_user_id",
        "tag_ids",
        "attachment_ids",
    )
    def _compute_display_value(self):
        for cell in self:
            cell.display_value = cell._get_display_value()

    @api.depends("column_id.view_group_ids", "column_id.edit_group_ids", "column_id.field_type")
    def _compute_access_flags(self):
        user = self.env.user
        for cell in self:
            cell.can_view = cell.column_id.can_user_view(user)
            cell.can_edit = cell.column_id.can_user_edit(user)

    @api.model_create_multi
    def create(self, vals_list):
        cells = super().create(vals_list)
        if not self.env.context.get("skip_board_access_check"):
            cells._check_column_edit_access()
            cells._validate_value_payload({})
            cells._sync_status_color()
        return cells

    def write(self, vals):
        trackable_fields = [
            "value_text",
            "value_number",
            "value_date",
            "value_status",
            "value_user_id",
            "tag_ids",
            "attachment_ids",
        ]
        should_track = any(field in vals for field in trackable_fields)
        previous_values = {cell.id: cell._get_display_value() for cell in self} if should_track else {}

        if should_track:
            self._check_column_edit_access()
            self._validate_value_payload(vals)

        result = super().write(vals)

        if should_track:
            for cell in self:
                cell._sync_status_color()
                current_value = cell._get_display_value()
                if previous_values.get(cell.id) != current_value:
                    self.env["monday.board.change.log"].create(
                        {
                            "board_id": cell.board_id.id,
                            "row_id": cell.row_id.id,
                            "column_id": cell.column_id.id,
                            "old_value": previous_values.get(cell.id, ""),
                            "new_value": current_value,
                            "user_id": self.env.user.id,
                        }
                    )
        return result

    def _check_column_edit_access(self):
        for cell in self:
            if not cell.column_id.can_user_edit(self.env.user):
                raise AccessError(
                    _("You do not have permission to edit the column '%s'.") % cell.column_id.name
                )

    def _validate_value_payload(self, vals):
        for cell in self:
            field_type = cell.column_id.field_type
            if field_type == "status":
                status_value = vals.get("value_status", cell.value_status)
                allowed = cell.column_id.status_option_ids.mapped("name")
                if status_value and allowed and status_value not in allowed:
                    raise ValidationError(_("Status value is not valid for this column."))
            if field_type == "tag" and "tag_ids" in vals:
                command_list = vals["tag_ids"]
                if isinstance(command_list, list):
                    tag_ids = set()
                    for command in command_list:
                        if command[0] == 6:
                            tag_ids = set(command[2])
                    if tag_ids:
                        invalid = self.env["monday.board.tag"].browse(list(tag_ids)).filtered(
                            lambda tag: tag.column_id != cell.column_id
                        )
                        if invalid:
                            raise ValidationError(_("Selected tags do not belong to this column."))

    def _get_row_context(self):
        self.ensure_one()
        context_map = {}
        for candidate in self.row_id.cell_ids:
            code = candidate.column_id.code
            context_map[code] = candidate._raw_value()
        return context_map

    def _raw_value(self):
        self.ensure_one()
        field_type = self.column_id.field_type
        if field_type in ("text", "time", "audit", "creation"):
            return self.value_text or ""
        if field_type == "number":
            return self.value_number or 0.0
        if field_type == "date":
            return self.value_date
        if field_type == "user":
            return self.value_user_id.name or ""
        if field_type == "status":
            return self.value_status or ""
        if field_type == "tag":
            return ", ".join(self.tag_ids.mapped("name"))
        if field_type == "attachment":
            return ", ".join(self.attachment_ids.mapped("name"))
        if field_type == "formula":
            return self._evaluate_formula()
        return ""

    def _evaluate_formula(self):
        self.ensure_one()
        expression = self.column_id.formula_expression or ""
        if not expression:
            return ""
        try:
            result = safe_eval(expression, self._get_row_context(), nocopy=True)
        except Exception as exc:
            return _("Formula error: %s") % exc
        return result

    def _sync_status_color(self):
        for cell in self.filtered(lambda c: c.column_id.field_type == "status"):
            option = cell.column_id.status_option_ids.filtered(
                lambda entry: entry.name == (cell.value_status or "")
            )[:1]
            if option:
                cell.value_status_color = option.color
            elif not cell.value_status:
                default_option = cell.column_id.status_option_ids.filtered("is_default")[:1]
                cell.value_status_color = default_option.color if default_option else "0"

    def _get_display_value(self):
        self.ensure_one()
        field_type = self.column_id.field_type
        if field_type in ("text", "time"):
            return self.value_text or ""
        if field_type == "number":
            return f"{self.value_number or 0.0:.2f}"
        if field_type == "date":
            return fields.Date.to_string(self.value_date) if self.value_date else ""
        if field_type == "user":
            return self.value_user_id.name or ""
        if field_type == "status":
            return self.value_status or ""
        if field_type == "tag":
            return ", ".join(self.tag_ids.mapped("name"))
        if field_type == "attachment":
            return ", ".join(self.attachment_ids.mapped("name"))
        if field_type == "formula":
            value = self._evaluate_formula()
            return "" if value is False or value is None else str(value)
        if field_type == "audit":
            return self.row_id.last_update_summary or ""
        if field_type == "creation":
            return self.row_id.creation_summary or ""
        return ""


class MondayBoardChangeLog(models.Model):
    _name = "monday.board.change.log"
    _description = "Monday Board Change Log"
    _order = "change_date desc, id desc"

    board_id = fields.Many2one("monday.board", required=True, ondelete="cascade")
    row_id = fields.Many2one("monday.board.row", required=True, ondelete="cascade")
    column_id = fields.Many2one("monday.board.column", required=True, ondelete="cascade")
    change_date = fields.Datetime(default=lambda self: fields.Datetime.now(), required=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    old_value = fields.Text()
    new_value = fields.Text()


class MondayBoardImportWizard(models.TransientModel):
    _name = "monday.board.import.wizard"
    _description = "Import Monday Board Wizard"

    target_board_id = fields.Many2one("monday.board", string="Replace Existing Board")
    import_mode = fields.Selection(
        [("api", "Monday API"), ("json", "Paste JSON")],
        default="api",
        required=True,
    )
    monday_token = fields.Char(string="Monday Token")
    monday_board_id = fields.Char(string="Monday Board ID")
    api_version = fields.Char(default="2026-04")
    monday_json = fields.Text(string="Board JSON")

    def action_import(self):
        self.ensure_one()
        payload = self._get_monday_payload()
        board_vals = {
            "name": payload.get("name") or _("Imported Monday Board"),
            "description": _("Imported from Monday board ID %s") % payload.get("id", ""),
        }
        board = self.target_board_id or self.env["monday.board"].create(board_vals)

        if self.target_board_id:
            board.column_ids.unlink()
            board.row_ids.unlink()

        self._import_columns(board, payload)
        self._import_rows(board, payload)

        return {
            "type": "ir.actions.act_window",
            "res_model": "monday.board",
            "res_id": board.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_monday_payload(self):
        self.ensure_one()
        if self.import_mode == "json":
            if not self.monday_json:
                raise UserError(_("Paste a Monday board JSON payload first."))
            try:
                payload = json.loads(self.monday_json)
            except json.JSONDecodeError as exc:
                raise UserError(_("Invalid JSON: %s") % exc) from exc
            return payload

        if not self.monday_token or not self.monday_board_id:
            raise UserError(_("Token and Board ID are required for API import."))
        return self._fetch_monday_board()

    def _fetch_monday_board(self):
        query = """
            query ImportBoard($boardId: [ID!]) {
              boards(ids: $boardId) {
                id
                name
                columns {
                  id
                  title
                  type
                  settings_str
                }
                items_page(limit: 500) {
                  items {
                    id
                    name
                    column_values {
                      id
                      text
                      value
                    }
                  }
                }
              }
            }
        """
        body = json.dumps(
            {"query": query, "variables": {"boardId": [str(self.monday_board_id)]}}
        ).encode("utf-8")
        req = request.Request(
            "https://api.monday.com/v2",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": self.monday_token,
                "API-Version": self.api_version or "2026-04",
            },
        )
        try:
            with request.urlopen(req) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise UserError(_("Monday API error %s: %s") % (exc.code, detail)) from exc
        except error.URLError as exc:
            raise UserError(_("Could not connect to Monday API: %s") % exc.reason) from exc

        if payload.get("errors"):
            raise UserError(
                _("Monday API returned errors: %s")
                % "; ".join(item.get("message", "Unknown error") for item in payload["errors"])
            )

        board = payload.get("data", {}).get("boards", [])
        if not board:
            raise UserError(_("The requested Monday board was not found."))
        return board[0]

    def _normalize_column_type(self, monday_type):
        monday_type = (monday_type or "").lower()
        if "status" in monday_type:
            return "status"
        if "date" in monday_type:
            return "date"
        if "number" in monday_type or "numeric" in monday_type:
            return "number"
        if "people" in monday_type:
            return "user"
        if "file" in monday_type:
            return "attachment"
        return "text"

    def _import_columns(self, board, payload):
        column_model = self.env["monday.board.column"]
        for sequence, column in enumerate(payload.get("columns", []), start=1):
            field_type = self._normalize_column_type(column.get("type"))
            new_column = column_model.create(
                {
                    "board_id": board.id,
                    "name": column.get("title") or column.get("id"),
                    "code": (column.get("id") or "").replace("-", "_"),
                    "sequence": sequence * 10,
                    "field_type": field_type,
                }
            )
            if field_type == "status":
                settings = {}
                try:
                    settings = json.loads(column.get("settings_str") or "{}")
                except json.JSONDecodeError:
                    settings = {}
                for status_sequence, (_, value) in enumerate(
                    sorted((settings.get("labels") or {}).items(), key=lambda item: item[0]),
                    start=1,
                ):
                    self.env["monday.board.status.option"].create(
                        {
                            "column_id": new_column.id,
                            "name": value,
                            "sequence": status_sequence * 10,
                        }
                    )

    def _extract_value_by_type(self, column, item_column_value):
        field_type = column.field_type
        if field_type == "number":
            try:
                return {"value_number": float(item_column_value.get("text") or 0)}
            except (ValueError, TypeError):
                return {"value_number": 0}
        if field_type == "date":
            value_payload = item_column_value.get("value")
            if value_payload:
                try:
                    parsed = json.loads(value_payload)
                    if parsed.get("date"):
                        return {"value_date": parsed["date"]}
                except json.JSONDecodeError:
                    pass
            return {"value_date": False}
        if field_type == "status":
            return {"value_status": item_column_value.get("text") or ""}
        return {"value_text": item_column_value.get("text") or ""}

    def _import_rows(self, board, payload):
        row_model = self.env["monday.board.row"]
        cell_model = self.env["monday.board.cell"]
        columns_by_code = {column.code: column for column in board.column_ids}
        payload_columns = {column.get("id"): column for column in payload.get("columns", [])}

        for sequence, item in enumerate(payload.get("items_page", {}).get("items", []), start=1):
            row = row_model.create({"board_id": board.id, "sequence": sequence * 10})
            values_by_id = {
                value.get("id"): value for value in item.get("column_values", []) if value.get("id")
            }
            for monday_column_id, monday_column in payload_columns.items():
                column = columns_by_code.get((monday_column_id or "").replace("-", "_"))
                if not column:
                    continue
                extracted = self._extract_value_by_type(column, values_by_id.get(monday_column_id, {}))
                cell = row.cell_ids.filtered(lambda candidate: candidate.column_id == column)[:1]
                if cell:
                    cell_model.browse(cell.id).sudo().write(extracted)
