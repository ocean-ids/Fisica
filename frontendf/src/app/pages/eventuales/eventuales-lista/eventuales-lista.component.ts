import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
  imports: [CommonModule, FormsModule],
  templateUrl: './eventuales-lista.component.html',
  styleUrl: './eventuales-lista.component.css',
})
export class EventualesListaComponent implements OnInit, OnDestroy {
  filas: HorasEventual[] = [];
  loading = false;
  fechaValor = '';      // YYYY-MM-DD (día que se está viendo)
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
    this.fechaValor = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
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
  }

  cargar(): void {
    // Registros del DÍA elegido (igual que Reporte de Asistencia / Asignaciones).
    const dia = this.fechaValor;
    if (!dia) { this.filas = []; return; }
    this.loading = true;
    this.srv.listar(dia, dia).subscribe({
      next: (rows) => { this.filas = rows || []; this.loading = false; },
      error: () => { this.filas = []; this.loading = false; },
    });
  }

  private norm(s: any): string {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  // Búsqueda en la tabla: cada palabra debe aparecer en el registro (en cualquier orden).
  get filasFiltradas(): HorasEventual[] {
    const tokens = this.norm(this.texto).split(/\s+/).filter(Boolean);
    if (!tokens.length) { return this.filas; }
    return this.filas.filter(f => {
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

  // Excel del día que se está viendo, con la búsqueda del buscador general aplicada.
  descargarExcel(): void {
    if (!this.fechaValor) { return; }
    const params: any = { fecha: this.fechaValor };
    if (this.texto.trim()) { params.q = this.texto.trim(); }
    const [y, m, d] = this.fechaValor.split('-');
    this.srv.exportarExcel(params).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `EVENTUALES ${d}-${m}-${y}.xlsx`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => Swal.fire({
        icon: 'error', title: 'Error',
        text: err?.status === 403 ? 'No autorizado' : 'No se pudo descargar el Excel',
      }),
    });
  }

  nuevo(): void { this.abrirDialog(null); }

  editar(f: HorasEventual): void { this.abrirDialog(f); }

  private abrirDialog(row: HorasEventual | null): void {
    const ref = this.dialog.open(EventualHorasDialogComponent, {
      width: '760px',
      maxWidth: '95vw',
      autoFocus: false,
      // Al crear, el formulario propone el día que se está viendo.
      data: { row: row || undefined, catalogo: this.catalogo, fechaDefecto: this.fechaValor },
    });
    ref.afterClosed().subscribe((res: HorasEventual | undefined) => {
      if (!res) { return; }
      // Si la fecha del servicio es otro día, la lista pasa a ese día (así se ve el registro).
      if (res.fecha && res.fecha !== this.fechaValor) { this.fechaValor = res.fecha; }
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
