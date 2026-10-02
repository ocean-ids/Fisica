import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { Subscription, debounceTime, distinctUntilChanged, map } from 'rxjs';
import Swal from 'sweetalert2';
import { HorasEventualService } from '../../../services/horas-eventual.service';
import { AuthService } from '../../../services/auth.service';
import { GlobalFilterStateService } from '../../../services/global-filter-state.service';
import { CatalogoHorasEventual, HorasEventual } from '../../../models/horas-eventual.model';
import { EventualHorasDialogComponent } from '../eventual-horas-dialog/eventual-horas-dialog.component';
import { EventualHistorialDialogComponent } from '../eventual-historial-dialog/eventual-historial-dialog.component';

@Component({
  selector: 'app-eventuales-lista',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatDatepickerModule, MatButtonToggleModule],
  templateUrl: './eventuales-lista.component.html',
  styleUrl: './eventuales-lista.component.css',
})
export class EventualesListaComponent implements OnInit, OnDestroy {
  filas: HorasEventual[] = [];
  loading = false;
  fechaDesde = '';      // YYYY-MM-DD: rango de fechas que se está viendo (Creado)
  fechaHasta = '';
  // Selector de rango (un solo calendario): start = Desde, end = Hasta.
  rangoForm = new FormGroup({
    start: new FormControl<Date | null>(null),
    end: new FormControl<Date | null>(null),
  });
  private rangoSub?: Subscription;
  // Turno que se está viendo. 'Ambos' = todos los registros (diurnos y nocturnos) en una sola lista.
  turnoFiltro: 'Ambos' | 'Diurno' | 'Nocturno' = 'Ambos';
  texto = '';           // búsqueda: viene del buscador GENERAL (barra superior)
  private catalogo: CatalogoHorasEventual | null = null;
  private filterSub?: Subscription;

  constructor(
    private srv: HorasEventualService,
    private dialog: MatDialog,
    private auth: AuthService,
    private globalFilter: GlobalFilterStateService,
    private router: Router,
  ) {}

  get puedeCrear(): boolean { return this.auth.hasPermission('CoreFisica.add_horaseventual'); }
  get puedeEditar(): boolean { return this.auth.hasPermission('CoreFisica.change_horaseventual'); }
  get puedeEliminar(): boolean { return this.auth.hasPermission('CoreFisica.delete_horaseventual'); }

  ngOnInit(): void {
    const d = new Date();
    // Por defecto: HOY (un solo día). En el calendario se puede elegir un rango.
    // El calendario abre SIN rango marcado: se marca solo cuando el usuario lo elige.
    this.fechaDesde = this.fechaHasta = this.aISO(d);
    // Al elegir el rango: se carga cuando están las dos fechas (Desde y Hasta).
    this.rangoSub = this.rangoForm.valueChanges.subscribe(() => this.aplicarRango());
    this.cargar();
    // El catálogo se carga una vez y se pasa al formulario (abre más rápido).
    this.srv.catalogo().subscribe({ next: (c) => (this.catalogo = c), error: () => (this.catalogo = null) });

    // Buscador general (barra superior): filtra la tabla de este módulo.
    this.filterSub = this.globalFilter.state$
      .pipe(
        map(state => {
          if (!this.router.url.startsWith('/dashboard/eventuales')) { return null; }
          const route = (state?.route || '').toString();
          if (route && !route.startsWith('/dashboard/eventuales')) { return null; }
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


  // Toma el rango elegido (Desde y Hasta) y carga los registros de esos días. Se llama al
  // cambiar las fechas y al cerrar el calendario; si el rango no cambió, no recarga.
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

  private filasCargadas = false;

  // Mes en el que abre el calendario: el del día que se está viendo.
  // (se guarda el mismo objeto Date para no crear uno nuevo en cada ciclo de pantalla).
  private _inicioCal: { iso: string; fecha: Date } | null = null;
  get inicioCalendario(): Date {
    if (!this._inicioCal || this._inicioCal.iso !== this.fechaDesde) {
      const [y, m, d] = this.fechaDesde.split('-').map(Number);
      this._inicioCal = { iso: this.fechaDesde, fecha: new Date(y, m - 1, d) };
    }
    return this._inicioCal.fecha;
  }

  // El rango es un solo día (Desde = Hasta).
  get esUnDia(): boolean { return !!this.fechaDesde && this.fechaDesde === this.fechaHasta; }

  // "30/9/2026" (mismo formato que el calendario)
  get diaTexto(): string {
    const [y, m, d] = this.fechaDesde.split('-').map(Number);
    return `${d}/${m}/${y}`;
  }

  // Fecha que se propone al crear: hoy si está dentro del rango; si no, el último día del rango.
  private fechaDefectoNuevo(): string {
    const hoy = this.aISO(new Date());
    return (hoy >= this.fechaDesde && hoy <= this.fechaHasta) ? hoy : this.fechaHasta;
  }

  cargar(): void {
    // Registros entre Desde y Hasta (ambos incluidos).
    if (!this.fechaDesde || !this.fechaHasta) { this.filas = []; return; }
    this.loading = true;
    this.srv.listar(this.fechaDesde, this.fechaHasta).subscribe({
      next: (rows) => {
        // Ordenados por nombre (apellidos y nombres) y, del mismo eventual, por fecha:
        // así los registros de una persona salen uno debajo del otro.
        this.filas = (rows || []).slice().sort((a, b) =>
          (a.persona || '').localeCompare(b.persona || '', 'es', { sensitivity: 'base' })
          || String(a.fecha || '').localeCompare(String(b.fecha || ''))
          || (Number(a.id) || 0) - (Number(b.id) || 0));
        this.filasCargadas = true;
        this.loading = false;
      },
      error: () => { this.filas = []; this.loading = false; },
    });
  }

  private norm(s: any): string {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  // Búsqueda en la tabla: cada palabra debe aparecer en el registro (en cualquier orden).
  get filasFiltradas(): HorasEventual[] {
    const tokens = this.norm(this.texto).split(/\s+/).filter(Boolean);
    const base = this.turnoFiltro === 'Ambos'
      ? this.filas
      : this.filas.filter(f => (f.turno || 'Diurno') === this.turnoFiltro);
    if (!tokens.length) { return base; }
    return base.filter(f => {
      const h = this.norm([f.persona, f.cedula, f.banco, f.numero_cuenta, f.cliente, f.instalacion, f.puesto].join(' '));
      return tokens.every(t => h.includes(t));
    });
  }

  get totalSolicitadas(): number {
    return this.filasFiltradas.reduce((acc, f) => acc + (Number(f.horas_solicitadas) || 0), 0);
  }

  get totalBonificacion(): number {
    return this.filasFiltradas.reduce((acc, f) => acc + (Number(f.bonificacion) || 0), 0);
  }

  get totalAdicionales(): number {
    return this.filasFiltradas.reduce((acc, f) => acc + (Number(f.horas_adicionales) || 0), 0);
  }

  get totalHoras(): number {
    return this.filasFiltradas.reduce((acc, f) => acc + (Number(f.horas) || 0), 0);
  }

  get totalValor(): number {
    return this.filasFiltradas.reduce((acc, f) => acc + (Number(f.valor_calculado) || 0), 0);
  }

  fechaDMA(v: any): string {
    if (!v) { return ''; }
    const [y, m, d] = String(v).slice(0, 10).split('-');
    return (y && m && d) ? `${d}/${m}/${y}` : String(v);
  }

  // Excel del rango que se está viendo, con la búsqueda del buscador general aplicada.
  descargarExcel(): void {
    if (!this.fechaDesde || !this.fechaHasta) { return; }
    const params: any = { desde: this.fechaDesde, hasta: this.fechaHasta };
    if (this.texto.trim()) { params.q = this.texto.trim(); }
    if (this.turnoFiltro !== 'Ambos') { params.turno = this.turnoFiltro; }
    const dma = (v: string) => v.split('-').reverse().join('-');
    const nombre = this.fechaDesde === this.fechaHasta
      ? `EVENTUALES ${dma(this.fechaDesde)}.xlsx`
      : `EVENTUALES ${dma(this.fechaDesde)} AL ${dma(this.fechaHasta)}.xlsx`;
    this.srv.exportarExcel(params).subscribe({
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
        text: err?.status === 403 ? 'No autorizado' : 'No se pudo descargar el Excel',
      }),
    });
  }

  // Solo se crea con UN día seleccionado (con un rango no se sabe en qué fecha sería).
  nuevo(): void { if (this.esUnDia && this.turnoFiltro !== 'Ambos') { this.abrirDialog(null); } }

  editar(f: HorasEventual): void { this.abrirDialog(f); }

  private abrirDialog(row: HorasEventual | null): void {
    const ref = this.dialog.open(EventualHorasDialogComponent, {
      width: '1000px',
      maxWidth: '95vw',
      autoFocus: false,
      // Al crear, el formulario propone el día que se está viendo.
      data: { row: row || undefined, catalogo: this.catalogo, fechaDefecto: this.fechaDefectoNuevo(),
        // El turno que se está viendo viene marcado en el formulario (Ambos no deja crear; solo Diurno o Nocturno).
        turnoDefecto: this.turnoFiltro === 'Nocturno' ? 'Nocturno' : 'Diurno' },
    });
    ref.afterClosed().subscribe((res: HorasEventual | undefined) => {
      if (!res) { return; }
      // Si la fecha quedó fuera del rango, la lista pasa a ese día (así se ve el registro).
      if (res.fecha && (res.fecha < this.fechaDesde || res.fecha > this.fechaHasta)) {
        this.fechaDesde = this.fechaHasta = res.fecha;
        this.rangoForm.reset({ start: null, end: null }, { emitEvent: false });
      }
      // Si el registro quedó en otro turno que el filtrado, la lista pasa a ese turno.
      if (this.turnoFiltro !== 'Ambos' && res.turno && res.turno !== this.turnoFiltro) {
        this.turnoFiltro = res.turno;
      }
      this.cargar();
    });
  }

  // Historial: quién creó el registro, quién lo modificó y qué cambió.
  verHistorial(f: HorasEventual): void {
    if (!f.id) { return; }
    this.dialog.open(EventualHistorialDialogComponent, {
      width: '1100px',
      maxWidth: '96vw',
      autoFocus: false,
      data: { row: f },
    });
  }

  eliminar(f: HorasEventual): void {
    if (!f.id) { return; }
    Swal.fire({
      title: '¿Eliminar registro?',
      text: `${f.persona || ''} — ${this.fechaDMA(f.fecha)} — ${f.horas} h`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
    }).then((r) => {
      if (r.isConfirmed) {
        this.srv.eliminar(f.id!).subscribe({ next: () => this.cargar(), error: () => this.cargar() });
      }
    });
  }
}
