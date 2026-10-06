import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';
import Swal from 'sweetalert2';
import { environment } from '@env/environment';
import { ReporteVacacionesService } from '../../services/reporte-vacaciones.service';
import { ReporteVacaciones } from '../../models/reporte-vacaciones.model';
import { SacavacacionesDialogComponent } from './sacavacaciones-dialog/sacavacaciones-dialog.component';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-sacavacaciones',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sacavacaciones.component.html',
  styleUrl: './sacavacaciones.component.css',
})
export class SacavacacionesComponent implements OnInit {
  filas: ReporteVacaciones[] = [];
  loading = false;

  // Filtro por año del "Desde" (0 = Todos), año actual por defecto.
  anioFiltro: number = new Date().getFullYear();
  anios: number[] = [];

  constructor(
    private srv: ReporteVacacionesService,
    private dialog: MatDialog,
    private http: HttpClient,
    private auth: AuthService,
  ) {}

  // Solo quien tiene el permiso crea / edita / elimina; los demás solo ven el reporte.
  get puedeCrear(): boolean { return this.auth.hasPermission('CoreFisica.add_reportevacaciones'); }
  get puedeEditar(): boolean { return this.auth.hasPermission('CoreFisica.change_reportevacaciones'); }
  get puedeEliminar(): boolean { return this.auth.hasPermission('CoreFisica.delete_reportevacaciones'); }

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.loading = true;
    this.srv.listar().subscribe({
      next: (rows) => {
        this.filas = rows || [];
        // Años disponibles según el campo 'anio' (con respaldo a la fecha "Desde").
        const set = new Set<number>();
        for (const f of this.filas) {
          const y = f.anio ?? this._anio(f.fecha_desde);
          if (y) { set.add(y); }
        }
        this.anios = Array.from(set).sort((a, b) => b - a);
        this.loading = false;
      },
      error: () => { this.filas = []; this.loading = false; },
    });
  }

  private _anio(v: any): number | null {
    if (!v) { return null; }
    const y = Number(String(v).slice(0, 4));
    return Number.isFinite(y) ? y : null;
  }

  // Filas mostradas según el año elegido (0 = Todos).
  get filasFiltradas(): ReporteVacaciones[] {
    if (!this.anioFiltro) { return this.filas; }
    return this.filas.filter(f => (f.anio ?? this._anio(f.fecha_desde)) === this.anioFiltro);
  }

  fechaDMA(v: any): string {
    if (!v) { return ''; }
    const [y, m, d] = String(v).slice(0, 10).split('-');
    return (y && m && d) ? `${d}/${m}/${y}` : String(v);
  }

  crear(): void {
    this.abrirDialog(null);
  }

  editar(f: ReporteVacaciones): void {
    this.abrirDialog(f);
  }

  private abrirDialog(row: ReporteVacaciones | null): void {
    const ref = this.dialog.open(SacavacacionesDialogComponent, {
      width: '710px',
      maxWidth: '95vw',
      // Al crear, el calendario se abre en el año del filtro (para no caer en el actual).
      data: { row: row || undefined, anioDefecto: this.anioFiltro || null },
    });
    ref.afterClosed().subscribe((res) => {
      if (!res) { return; }
      const editando = !!row?.id;
      const req = editando ? this.srv.actualizar(row!.id!, res) : this.srv.crear(res);
      req.subscribe({
        next: () => {
          this.cargar();
          Swal.fire({
            icon: 'success', title: editando ? 'Registro actualizado' : 'Registro creado',
            timer: 1500, showConfirmButton: false,
          });
        },
        error: (err) => {
          this.cargar();
          Swal.fire({
            icon: 'error', title: editando ? 'No se pudo actualizar' : 'No se pudo crear',
            text: this.mensajeError(err),
          });
        },
      });
    });
  }

  // Texto del error del servidor (validaciones de DRF: {campo: ['mensaje']}) o uno genérico.
  private mensajeError(err: any): string {
    const e = err?.error;
    if (err?.status === 403) { return 'No tienes permiso para esta acción.'; }
    if (typeof e === 'string' && e.length < 300) { return e; }
    if (e && typeof e === 'object') {
      const partes = Object.entries(e).map(([k, v]) =>
        `${k === 'detail' || k === 'error' ? '' : k + ': '}${Array.isArray(v) ? v.join(' ') : v}`);
      if (partes.length) { return partes.join(' | '); }
    }
    return 'Revisa los datos e intenta de nuevo.';
  }

  eliminar(f: ReporteVacaciones): void {
    if (!f.id) { return; }
    Swal.fire({
      title: '¿Eliminar registro?',
      text: `${f.persona_sale || ''}`.trim(),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
    }).then((r) => {
      if (r.isConfirmed) {
        this.srv.eliminar(f.id!).subscribe({
          next: () => {
            this.cargar();
            Swal.fire({ icon: 'success', title: 'Registro eliminado', timer: 1500, showConfirmButton: false });
          },
          error: (err) => {
            this.cargar();
            Swal.fire({ icon: 'error', title: 'No se pudo eliminar', text: this.mensajeError(err) });
          },
        });
      }
    });
  }

  exportar(): void {
    const url = `${environment.apiUrl}/reporte-vacaciones/exportar-excel/`;
    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: (blob) => saveAs(blob, 'reporte_vacaciones.xlsx'),
      error: () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo descargar el reporte' }),
    });
  }
}
