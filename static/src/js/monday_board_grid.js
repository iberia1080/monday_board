/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class MondayBoardGrid extends Component {
    static template = "monday_board.MondayBoardGrid";

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            board: null,
            columns: [],
            rows: [],
            filters: {
                movimiento: "",
                sucursal: "",
                query: "",
            },
        });

        onWillStart(async () => {
            await this.loadBoard();
        });
    }

    get boardId() {
        return this.props.action.context.board_id;
    }

    async loadBoard() {
        this.state.loading = true;
        const payload = await this.rpc(`/monday_board/grid_data/${this.boardId}`, {});
        this.state.board = payload.board;
        this.state.columns = payload.columns;
        this.state.rows = payload.rows;
        this.state.loading = false;
    }

    get filteredRows() {
        return this.state.rows.filter((row) => {
            const movimientoCell = row.cells.find((cell) => cell.column_code === "movimiento");
            const sucursalCell = row.cells.find((cell) => cell.column_code === "sucursal");
            const query = this.state.filters.query.trim().toLowerCase();
            const movimiento = this.state.filters.movimiento;
            const sucursal = this.state.filters.sucursal;
            const haystack = row.cells.map((cell) => String(cell.display_value || "")).join(" ").toLowerCase();

            if (movimiento && !movimientoCell?.tag_labels?.some((tag) => tag.name === movimiento)) {
                return false;
            }
            if (sucursal && !sucursalCell?.tag_labels?.some((tag) => tag.name === sucursal)) {
                return false;
            }
            if (query && !haystack.includes(query)) {
                return false;
            }
            return true;
        });
    }

    get movimientoOptions() {
        const column = this.state.columns.find((item) => item.code === "movimiento");
        return column?.tag_options || [];
    }

    get sucursalOptions() {
        const column = this.state.columns.find((item) => item.code === "sucursal");
        return column?.tag_options || [];
    }

    onFilterInput(ev) {
        this.state.filters.query = ev.target.value;
    }

    onSelectFilter(key, ev) {
        this.state.filters[key] = ev.target.value;
    }

    clearFilters() {
        this.state.filters.movimiento = "";
        this.state.filters.sucursal = "";
        this.state.filters.query = "";
    }

    async onCellChange(row, column, ev) {
        const value = ev.target.value;
        await this.saveCell(row.id, column.code, { value });
    }

    async onTagFilterClick(columnCode, tagName) {
        if (columnCode === "movimiento") {
            this.state.filters.movimiento = tagName;
        } else if (columnCode === "sucursal") {
            this.state.filters.sucursal = tagName;
        }
    }

    async saveCell(rowId, columnCode, payload) {
        try {
            const data = await this.rpc("/monday_board/update_cell", {
                board_id: this.boardId,
                row_id: rowId,
                column_code: columnCode,
                ...payload,
            });
            this.state.board = data.board;
            this.state.columns = data.columns;
            this.state.rows = data.rows;
            this.notification.add("Cambio guardado", { type: "success" });
        } catch (error) {
            this.notification.add("No se pudo guardar el cambio.", { type: "danger" });
        }
    }

    async openRowHistory(row) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Historial de Cambios",
            res_model: "monday.board.change.log",
            view_mode: "list,form",
            domain: [["row_id", "=", row.id]],
            target: "current",
        });
    }

    formatCell(column, cell) {
        if (column.field_type === "attachment") {
            return cell.attachment_count ? `${cell.attachment_count} archivo(s)` : "";
        }
        return cell.display_value || "";
    }

    statusClass(cell) {
        return `o_monday_status o_monday_status_${cell.status_color || "0"}`;
    }
}

registry.category("actions").add("monday_board.grid", MondayBoardGrid);
