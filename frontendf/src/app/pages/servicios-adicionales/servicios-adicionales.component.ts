import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { Subscription, debounceTime, distinctUntilChanged, map } from 'rxjs';
import Swal from 'sweetalert2';
import { ServicioAdicional, ServiciosAdicionalesService } from '../../services/servicios-adicionales.service';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';
import { AuthService } from '../../services/auth.service';
import { ServicioAdicionalDialogComponent } from './servicio-adicional-dialog/servicio-adicional-dialog.component';

// Servicios Adicionales (formato FR-REPORTE DE PUESTO ADICIONAL): lista por rango de fechas, Nuevo registro y
// editar. También se llenan desde la asistencia al guardar una fila como ADICIONAL. El precio, solo con su permiso.
@Component({
  selector: 'app-servicios-adicionales',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatDatepickerModule, MatButtonToggleModule, MatMenuModule],
  templateUrl: './servicios-adicionales.component.html',
  styleUrl: './servicios-adicionales.component.css',
})
export class ServiciosAdicionalesComponent implements OnInit, OnDestroy {
  filas: ServicioAdicional[] = [];
  loading = false;
  fechaDesde = '';      // YYYY-MM-DD: rango de fechas que se está viendo
  fechaHasta = '';
  // Selector de rango (un solo calendario): start = Desde, end = Hasta.
  rangoForm = new FormGroup({
    start: new FormControl<Date | null>(null),
    end: new FormControl<Date | null>(null),
  });
  private rangoSub?: Subscription;
  // Turno que se está viendo. 'Ambos' = diurnos y nocturnos en una sola lista.
  turnoFiltro: 'Ambos' | 'Diurno' | 'Nocturno' = 'Ambos';
  texto = '';           // búsqueda: viene del buscador GENERAL (barra superior)
  private filterSub?: Subscription;
  private filasCargadas = false;

  constructor(
    private srv: ServiciosAdicionalesService,
    private globalFilter: GlobalFilterStateService,
    private router: Router,
    private dialog: MatDialog,
    private auth: AuthService,
  ) {}

  get puedeCrear(): boolean { return this.auth.hasPermission('CoreFisica.add_servicioadicional'); }
  get puedeEditar(): boolean { return this.auth.hasPermission('CoreFisica.change_servicioadicional'); }
  get puedePrecio(): boolean { return this.auth.hasPermission('CoreFisica.editar_precio_servicioadicional'); }

  ngOnInit(): void {
    // Por defecto: HOY (un solo día). En el calendario se puede elegir un rango.
    this.fechaDesde = this.fechaHasta = this.aISO(new Date());
    this.rangoSub = this.rangoForm.valueChanges.subscribe(() => this.aplicarRango());
    this.cargar();

    // Buscador general (barra superior): filtra la tabla de este módulo.
    this.filterSub = this.globalFilter.state$
      .pipe(
        map(state => {
          if (!this.router.url.startsWith('/dashboard/servicios-adicionales')) { return null; }
          const route = (state?.route || '').toString();
          if (route && !route.startsWith('/dashboard/servicios-adicionales')) { return null; }
          return (state?.query || '').trim();
        }),
        distinctUntilChanged(),
        debounceTime(200),
      )
      .subscribe(q => { if (q !== null) { this.texto = q; } });
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
    this.rangoSub?.unsubscribe();
  }

  private aISO(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  // Toma el rango elegido (Desde y Hasta) y carga esos días; si el rango no cambió, no recarga.
  aplicarRango(): void {
    const v = this.rangoForm.value;
    if (!v.start || !v.end) { return; }
    const desde = this.aISO(v.start);
    const hasta = this.aISO(v.end);
    if (desde === this.fechaDesde && hasta === this.fechaHasta && this.filasCargadas) { return; }
    this.fechaDesde = desde;
    this.fechaHasta = hasta;
    this.cargar();
  }

  // Mes en el que abre el calendario: el del día que se está viendo (mismo objeto Date mientras no cambie).
  private _inicioCal: { iso: string; fecha: Date } | null = null;
  get inicioCalendario(): Date {
    if (!this._inicioCal || this._inicioCal.iso !== this.fechaDesde) {
      const [y, m, d] = this.fechaDesde.split('-').map(Number);
      this._inicioCal = { iso: this.fechaDesde, fecha: new Date(y, m - 1, d) };
    }
    return this._inicioCal.fecha;
  }

  get esUnDia(): boolean { return !!this.fechaDesde && this.fechaDesde === this.fechaHasta; }

  // "1/10/2026" a partir de YYYY-MM-DD (texto Desde / Hasta del selector).
  fechaCorta(iso: string): string {
    const [y, m, d] = (iso || '').split('-').map(Number);
    return (y && m && d) ? `${d}/${m}/${y}` : '';
  }

  fechaDMA(v: any): string {
    if (!v) { return ''; }
    const [y, m, d] = String(v).slice(0, 10).split('-');
    return (y && m && d) ? `${d}/${m}/${y}` : String(v);
  }

  cargar(): void {
    if (!this.fechaDesde || !this.fechaHasta) { this.filas = []; return; }
    this.loading = true;
    this.srv.listar(this.fechaDesde, this.fechaHasta).subscribe({
      next: (rows) => { this.filas = rows || []; this.filasCargadas = true; this.loading = false; },
      error: (err) => {
        this.filas = [];
        this.loading = false;
        Swal.fire({ icon: 'error', title: 'Error',
          text: err?.status === 403 ? 'No autorizado' : (err?.error?.error || 'No se pudieron cargar los servicios adicionales') });
      },
    });
  }

  private norm(s: any): string {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  // Turno elegido y búsqueda: cada palabra debe aparecer en el registro (en cualquier orden).
  get filasFiltradas(): ServicioAdicional[] {
    const base = this.turnoFiltro === 'Ambos' ? this.filas : this.filas.filter(f => f.turno === this.turnoFiltro);
    const tokens = this.norm(this.texto).split(/\s+/).filter(Boolean);
    if (!tokens.length) { return base; }
    return base.filter(f => {
      const h = this.norm([f.cliente_texto, f.cliente, f.puesto, f.persona, f.solicitado_por, f.recibido_por, f.medio, f.horario].join(' '));
      return tokens.every(t => h.includes(t));
    });
  }

  // Excel del rango que se está viendo (formato FR: una pestaña por día con el turno Diurno y Nocturno).
  descargarExcel(): void { this.descargar('xlsx'); }

  // PDF del rango que se está viendo (formato FR: una página por día con el turno Diurno y Nocturno).
  descargarPdf(): void { this.descargar('pdf'); }

  private descargar(tipo: 'xlsx' | 'pdf'): void {
    if (!this.fechaDesde || !this.fechaHasta) { return; }
    const params: any = { desde: this.fechaDesde, hasta: this.fechaHasta };
    if (this.texto.trim()) { params.q = this.texto.trim(); }
    const dma = (v: string) => v.split('-').reverse().join('-');
    const nombre = this.esUnDia
      ? `SERVICIOS ADICIONALES ${dma(this.fechaDesde)}.${tipo}`
      : `SERVICIOS ADICIONALES ${dma(this.fechaDesde)} AL ${dma(this.fechaHasta)}.${tipo}`;
    const obs = tipo === 'pdf' ? this.srv.exportarPdf(params) : this.srv.exportarExcel(params);
    obs.subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nombre;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => Swal.fire({
        icon: 'error', title: 'Error',
        text: err?.status === 403 ? 'No autorizado' : (tipo === 'pdf' ? 'No se pudo descargar el PDF' : 'No se pudo descargar el Excel'),
      }),
    });
  }

  // Nuevo registro: con UN día y un turno elegidos (con un rango o en Ambos no se sabe la fecha o el turno).
  nuevo(): void {
    if (!this.esUnDia || this.turnoFiltro === 'Ambos') { return; }
    this.abrir({ fecha: this.fechaDesde, turno: this.turnoFiltro });
  }

  editar(f: ServicioAdicional): void { this.abrir({ ...f }); }

  // Solo los agregados con el botón de la asistencia (los demás se quitan cambiando la asistencia).
  eliminar(f: ServicioAdicional): void {
    if (!f.id) { return; }
    Swal.fire({
      title: '¿Eliminar servicio adicional?', text: `${f.cliente_texto || ''} · ${f.persona || ''}`.trim(),
      icon: 'warning', showCancelButton: true, confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar',
    }).then(r => {
      if (!r.isConfirmed) { return; }
      this.srv.eliminar(f.id!).subscribe({
        next: () => { this.cargar(); Swal.fire({ icon: 'success', title: 'Eliminado', timer: 1300, showConfirmButton: false }); },
        error: (err) => Swal.fire({ icon: 'error', title: 'No se pudo eliminar', text: err?.error?.error || '' }),
      });
    });
  }

  private abrir(row: Partial<ServicioAdicional>): void {
    const ref = this.dialog.open(ServicioAdicionalDialogComponent, {
      width: '900px', maxWidth: '95vw', autoFocus: false, data: { row },
    });
    ref.afterClosed().subscribe((res?: ServicioAdicional) => { if (res) { this.cargar(); } });
  }
}
