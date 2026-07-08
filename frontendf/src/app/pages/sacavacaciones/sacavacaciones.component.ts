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
  ) {}

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.loading = true;
    this.srv.listar().subscribe({
      next: (rows) => {
        this.filas = rows || [];
        // Años disponibles según la fecha "Desde" de los registros.
        const set = new Set<number>();
        for (const f of this.filas) {
          const y = this._anio(f.fecha_desde);
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
    return this.filas.filter(f => this._anio(f.fecha_desde) === this.anioFiltro);
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
      width: '560px',
      maxWidth: '95vw',
      data: { row: row || undefined },
    });
    ref.afterClosed().subscribe((res) => {
      if (!res) { return; }
      if (row?.id) {
        this.srv.actualizar(row.id, res).subscribe({ next: () => this.cargar(), error: () => this.cargar() });
      } else {
        this.srv.crear(res).subscribe({ next: () => this.cargar(), error: () => this.cargar() });
      }
    });
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
        this.srv.eliminar(f.id!).subscribe({ next: () => this.cargar(), error: () => this.cargar() });
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
