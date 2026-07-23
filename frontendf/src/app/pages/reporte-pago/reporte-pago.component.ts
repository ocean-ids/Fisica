import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ReportePagoService } from '../../services/reporte-pago.service';
import { ReportePago, TarifaPago } from '../../models/reporte-pago.model';
import { ResumenMensualModalComponent } from './resumen-mensual-modal/resumen-mensual-modal.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-reporte-pago',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonToggleModule, MatDialogModule],
  templateUrl: './reporte-pago.component.html',
  styleUrl: './reporte-pago.component.css',
})
export class ReportePagoComponent implements OnInit {
  filtroFecha = new Date().toISOString().slice(0, 10);
  filtroTurno: 'Diurno' | 'Nocturno' = localStorage.getItem('rp_turno') === 'Nocturno' ? 'Nocturno' : 'Diurno';
  filas: ReportePago[] = [];
  tarifas: TarifaPago[] = [];
  loading = false;

  sel: ReportePago | null = null;      // fila activa en el formulario
  selTarifaId: number | null = null;   // rango horario elegido (id de tarifa)

  constructor(private srv: ReportePagoService, private dialog: MatDialog) {}

  ngOnInit(): void {
    this.srv.listarTarifas().subscribe({ next: (t) => (this.tarifas = t || []), error: () => (this.tarifas = []) });
    this.cargar();
  }

  // Abre el resumen mensual en un modal (mes/año/tipo de servicio, totales y por persona).
  abrirResumenMensual(): void {
    this.dialog.open(ResumenMensualModalComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { tipos: this.tipos },
    });
  }

  cargar(): void {
    localStorage.setItem('rp_turno', this.filtroTurno);
    this.loading = true;
    this.sel = null;
    this.selTarifaId = null;
    this.srv.listar(this.filtroFecha, this.filtroTurno).subscribe({
      next: (rows) => { this.filas = rows || []; this.loading = false; },
      error: () => { this.filas = []; this.loading = false; },
    });
  }

  onFechaChange(e: Event): void {
    this.filtroFecha = (e.target as HTMLInputElement).value;
    this.cargar();
  }

  // Tipos de servicio disponibles (de las tarifas), en orden.
  get tipos(): string[] {
    const out: string[] = [];
    for (const t of this.tarifas) { if (!out.includes(t.tipo_servicio)) { out.push(t.tipo_servicio); } }
    return out;
  }

  // Bandas (rangos horarios) del tipo elegido.
  rangosDe(tipo?: string): TarifaPago[] {
    if (!tipo) { return []; }
    return this.tarifas.filter(t => t.tipo_servicio === tipo);
  }

  // Tarifa que corresponde a un pago ya guardado (por tipo + horas dentro de la banda).
  private tarifaDe(f: ReportePago): TarifaPago | undefined {
    const h = Number(f.horas || 0);
    return this.tarifas.find(t => t.tipo_servicio === f.tipo_servicio && t.horas_min <= h && t.horas_max >= h);
  }

  seleccionar(f: ReportePago): void {
    this.sel = f;
    this.selTarifaId = this.tarifaDe(f)?.id ?? null;
  }

  // Al cambiar el tipo, se reinicia el rango (las bandas cambian).
  onTipoChange(): void {
    if (!this.sel) { return; }
    this.selTarifaId = null;
    this.sel.horas = null;
    this.sel.valor_calculado = 0;
  }

  // Al elegir el rango, se fija horas y se previsualiza el valor.
  onRangoChange(): void {
    if (!this.sel) { return; }
    const t = this.tarifas.find(x => x.id === Number(this.selTarifaId));
    if (t) {
      this.sel.horas = t.horas_max;
      this.sel.valor_calculado = t.valor;
    } else {
      this.sel.horas = null;
      this.sel.valor_calculado = 0;
    }
  }

  rangoLabel(t: TarifaPago): string {
    const r = t.horas_min === t.horas_max ? `${t.horas_min} h` : `${t.horas_min}-${t.horas_max} h`;
    return `${r}  →  $${this.num(t.valor).toFixed(2)}`;
  }

  guardar(): void {
    if (!this.sel?.id) { return; }
    const f = this.sel;
    const data: Partial<ReportePago> = {
      tipo_servicio: f.tipo_servicio || '',
      horas: f.horas ?? null,
      valor_total: f.valor_total ?? null,
      referencia: f.referencia || '',
    };
    this.srv.actualizar(f.id!, data).subscribe({
      next: (r) => {
        Object.assign(f, r);
        Swal.fire({ icon: 'success', title: 'Guardado', toast: true, position: 'top-end', showConfirmButton: false, timer: 1200 });
      },
      error: () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo guardar' }),
    });
  }

  num(v: any): number { return Number(v || 0); }

  valorFila(f: ReportePago): number {
    const total = this.num(f.valor_total);
    return total > 0 ? total : this.num(f.valor_calculado);
  }

  get totalPagar(): number {
    return this.filas.reduce((s, f) => s + this.valorFila(f), 0);
  }
}
