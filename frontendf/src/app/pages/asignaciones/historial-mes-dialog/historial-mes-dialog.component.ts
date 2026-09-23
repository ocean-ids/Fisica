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
  templateUrl: './historial-mes-dialog.component.html',
  styleUrl: './historial-mes-dialog.component.css',
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
