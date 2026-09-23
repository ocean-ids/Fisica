import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AsignacionService } from '../../../services/asignacion.service';
import { ReporteAsistenciaService } from '../../../services/reporte-asistencia.service';

interface HistItem {
  hora: string; usuario: string; accion: string; accion_key: string;
  cliente: string; puesto: string; antes: string; despues: string; persona: string;
  asignacion_id: number | null;
}
interface HistDia { fecha: string; items: HistItem[]; }

@Component({
  selector: 'app-historial-mes-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>Historial del mes · Movimientos por día</h2>
    <mat-dialog-content class="hist-content">
      <div class="hist-sub">
        {{ nombreMes }} {{ data.anio }}
        <span *ngIf="!cargando"> · {{ totalFiltrado }}<span *ngIf="totalFiltrado !== total"> de {{ total }}</span> movimiento(s)</span>
      </div>

      <div class="hist-filtros" *ngIf="!cargando && total > 0">
        <input type="text" class="hist-search" [(ngModel)]="filtroTexto" (ngModelChange)="aplicarFiltro()"
               placeholder="Buscar puesto, persona o usuario…">
        <select class="hist-select" [(ngModel)]="filtroAccion" (ngModelChange)="aplicarFiltro()">
          <option *ngFor="let a of accionesOpc" [value]="a.k">{{ a.l }}</option>
        </select>
        <button *ngIf="filtroTexto || filtroAccion" class="hist-limpiar" type="button" (click)="limpiarFiltro()">Limpiar</button>
      </div>

      <div *ngIf="cargando" class="hist-msg">Cargando…</div>
      <div *ngIf="!cargando && dias.length === 0" class="hist-msg">
        No hay movimientos registrados en este mes.
      </div>
      <div *ngIf="!cargando && dias.length > 0 && diasFiltrados.length === 0" class="hist-msg">
        No hay movimientos que coincidan con el filtro.
      </div>

      <table class="hist-table" *ngIf="!cargando && diasFiltrados.length > 0">
        <thead>
          <tr>
            <th class="c-hora">Hora</th>
            <th class="c-accion">Acción</th>
            <th class="c-puesto">Puesto</th>
            <th class="c-cliente">Cliente</th>
            <th class="c-persona">Guardia anterior</th>
            <th class="c-persona">Guardia actual</th>
            <th class="c-user">Usuario</th>
          </tr>
        </thead>
        <tbody>
          <ng-container *ngFor="let d of diasFiltrados">
            <tr class="hist-dia-row">
              <td colspan="7">{{ formatoDia(d.fecha) }}
                <span class="hist-dia-count">{{ d.items.length }}</span>
              </td>
            </tr>
            <ng-container *ngFor="let it of d.items">
              <tr class="hist-row" [class.clickable]="it.asignacion_id" (click)="toggleTimeline(it)">
                <td class="c-hora">{{ it.hora || '—' }}</td>
                <td class="c-accion">
                  <span class="hist-badge" [ngClass]="claseAccion(it.accion_key)">{{ it.accion }}</span>
                </td>
                <td class="c-puesto">
                  <span *ngIf="it.asignacion_id" class="tl-caret">{{ expandedItem === it ? '▾' : '▸' }}</span>
                  {{ it.puesto || '—' }}
                </td>
                <td class="c-cliente">{{ it.cliente || '—' }}</td>
                <td class="c-persona">{{ it.accion_key === 'CAMBIO' ? it.antes : '—' }}</td>
                <td class="c-persona strong">{{ it.accion_key === 'CAMBIO' ? it.despues : (it.persona || '—') }}</td>
                <td class="c-user">{{ it.usuario || '—' }}</td>
              </tr>
              <tr *ngIf="expandedItem === it" class="hist-detail-row">
                <td colspan="7">
                  <div *ngIf="tlLoading" class="tl-msg">Cargando guardias del puesto…</div>
                  <div *ngIf="!tlLoading">
                    <div class="tl-title">Guardias que han estado en <b>{{ tlPuesto || it.puesto }}</b></div>
                    <table class="tl-table">
                      <tr *ngFor="let p of tlPorPersona">
                        <td class="tl-nom">{{ p.persona }}</td>
                        <td class="tl-rango">{{ p.desde }}<span *ngIf="p.hasta"> — {{ p.hasta }}</span></td>
                      </tr>
                      <tr *ngIf="!tlPorPersona.length"><td class="tl-msg">Sin historial de guardias.</td></tr>
                    </table>
                  </div>
                </td>
              </tr>
            </ng-container>
          </ng-container>
        </tbody>
      </table>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="cerrar()">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .hist-content { min-width: 960px; max-width: 1140px; max-height: 72vh; }
    .hist-sub { font-weight: 600; color: #374151; margin-bottom: 10px; text-transform: capitalize; }
    .hist-msg { color: #6b7280; padding: 16px 0; text-align: center; }
    .hist-filtros { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
    .hist-search { flex: 1; padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; }
    .hist-select { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; background: #fff; }
    .hist-limpiar { padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; background: #f9fafb; cursor: pointer; font-size: 12px; }

    .hist-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .hist-table thead th {
      position: sticky; top: 0; z-index: 1; background: #f3f4f6; color: #374151;
      text-align: left; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: .3px;
      padding: 8px 10px; border-bottom: 2px solid #e5e7eb;
    }
    .hist-table td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    .hist-row:hover td { background: #f9fafb; }
    .hist-dia-row td {
      background: #eef2ff; color: #1e293b; font-weight: 700; text-transform: capitalize;
      border-bottom: 1px solid #e5e7eb;
    }
    .hist-dia-count { background: #dbeafe; color: #1e40af; border-radius: 10px; font-size: 11px; padding: 1px 8px; font-weight: 700; margin-left: 6px; }
    .c-hora { width: 56px; color: #6b7280; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .c-accion { width: 130px; }
    .c-puesto { color: #111827; font-weight: 600; }
    .c-cliente { color: #6b7280; }
    .c-persona { color: #374151; }
    .c-persona.strong { color: #111827; font-weight: 600; }
    .c-user { color: #6b7280; white-space: nowrap; }
    .hist-badge { display: inline-block; font-size: 10px; font-weight: 700; border-radius: 10px; padding: 2px 8px; white-space: nowrap; }
    .acc-create { background: #dcfce7; color: #166534; }
    .acc-update { background: #dbeafe; color: #1e40af; }
    .acc-delete { background: #fee2e2; color: #991b1b; }
    .acc-cambio { background: #ede9fe; color: #6d28d9; }
    .hist-row.clickable { cursor: pointer; }
    .tl-caret { color: #6d28d9; font-weight: 700; margin-right: 4px; }
    .hist-detail-row td { background: #faf5ff; padding: 10px 16px; }
    .tl-title { font-weight: 600; color: #4b5563; margin-bottom: 6px; }
    .tl-table { width: auto; border-collapse: collapse; }
    .tl-table td { padding: 4px 14px 4px 0; border-bottom: 1px dashed #e9d5ff; font-size: 13px; }
    .tl-nom { color: #111827; font-weight: 600; }
    .tl-rango { color: #6b7280; font-variant-numeric: tabular-nums; }
    .tl-msg { color: #6b7280; }
  `],
})
export class HistorialMesDialogComponent implements OnInit {
  cargando = true;
  total = 0;
  dias: HistDia[] = [];
  diasFiltrados: HistDia[] = [];
  totalFiltrado = 0;
  nombreMes = '';

  filtroTexto = '';
  filtroAccion = '';

  // Detalle: al hacer click en una fila con puesto, se muestra la lista de guardias que
  // han estado en ese puesto (línea de tiempo por persona).
  expandedItem: HistItem | null = null;
  tlLoading = false;
  tlPuesto = '';
  tlPorPersona: Array<{ persona: string; desde: string; hasta: string }> = [];
  private tlCache: { [asigId: number]: { puesto: string; por_persona: any[] } } = {};

  readonly accionesOpc = [
    { k: '', l: 'Todas las acciones' },
    { k: 'CREATE', l: 'Puesto creado' },
    { k: 'DELETE', l: 'Puesto eliminado' },
    { k: 'UPDATE', l: 'Editó' },
    { k: 'CAMBIO', l: 'Cambio de guardia' },
  ];

  private readonly meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  constructor(
    private asignacionService: AsignacionService,
    private reporteSvc: ReporteAsistenciaService,
    private dialogRef: MatDialogRef<HistorialMesDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { mes: number; anio: number }
  ) {
    this.nombreMes = this.meses[this.data?.mes] || '';
  }

  // Al hacer click en una fila con puesto: muestra/oculta la lista de todos los guardias
  // que han estado en ese puesto (con sus rangos de fechas).
  toggleTimeline(it: HistItem): void {
    if (!it.asignacion_id) { return; }
    if (this.expandedItem === it) { this.expandedItem = null; return; }
    this.expandedItem = it;
    const cached = this.tlCache[it.asignacion_id];
    if (cached) {
      this.tlPuesto = cached.puesto;
      this.tlPorPersona = cached.por_persona;
      this.tlLoading = false;
      return;
    }
    this.tlLoading = true;
    this.tlPuesto = it.puesto;
    this.tlPorPersona = [];
    this.reporteSvc.getHistorialPuesto(it.asignacion_id).subscribe({
      next: (res: any) => {
        const data = { puesto: res?.puesto || it.puesto, por_persona: res?.por_persona || [] };
        this.tlCache[it.asignacion_id!] = data;
        // Solo aplicar si sigue expandida la misma fila.
        if (this.expandedItem === it) {
          this.tlPuesto = data.puesto;
          this.tlPorPersona = data.por_persona;
        }
        this.tlLoading = false;
      },
      error: () => { this.tlLoading = false; },
    });
  }

  ngOnInit(): void {
    this.asignacionService.historialMes(this.data.mes, this.data.anio).subscribe({
      next: (res) => {
        this.total = res?.total || 0;
        this.dias = res?.dias || [];
        this.aplicarFiltro();
        this.cargando = false;
      },
      error: () => { this.cargando = false; },
    });
  }

  private _norm(s: string): string {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  aplicarFiltro(): void {
    const q = this._norm(this.filtroTexto).trim();
    const tokens = q ? q.split(/\s+/) : [];
    const acc = this.filtroAccion;
    let count = 0;
    const res: HistDia[] = [];
    for (const d of this.dias) {
      const items = d.items.filter((it) => {
        if (acc && it.accion_key !== acc) { return false; }
        if (!tokens.length) { return true; }
        const hay = this._norm(`${it.puesto} ${it.cliente} ${it.persona} ${it.antes} ${it.despues} ${it.usuario} ${it.accion}`);
        return tokens.every((t) => hay.includes(t));
      });
      if (items.length) { res.push({ fecha: d.fecha, items }); count += items.length; }
    }
    this.diasFiltrados = res;
    this.totalFiltrado = count;
  }

  limpiarFiltro(): void {
    this.filtroTexto = '';
    this.filtroAccion = '';
    this.aplicarFiltro();
  }

  claseAccion(key: string): string {
    if (key === 'CREATE') return 'acc-create';
    if (key === 'DELETE') return 'acc-delete';
    if (key === 'CAMBIO') return 'acc-cambio';
    return 'acc-update';
  }

  formatoDia(iso: string): string {
    // iso = YYYY-MM-DD -> "Lunes 21/09/2026"
    const [y, m, d] = (iso || '').split('-').map(Number);
    if (!y) return iso;
    const fecha = new Date(y, (m || 1) - 1, d || 1);
    const dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
    const nd = dias[fecha.getDay()] || '';
    const dd = String(d).padStart(2, '0');
    const mm = String(m).padStart(2, '0');
    return `${nd} ${dd}/${mm}/${y}`;
  }

  cerrar(): void { this.dialogRef.close(); }
}
