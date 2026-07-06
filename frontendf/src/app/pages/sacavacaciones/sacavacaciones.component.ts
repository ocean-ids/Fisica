import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
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
  imports: [CommonModule],
  templateUrl: './sacavacaciones.component.html',
  styleUrl: './sacavacaciones.component.css',
})
export class SacavacacionesComponent implements OnInit {
  filas: ReporteVacaciones[] = [];
  loading = false;

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
      next: (rows) => { this.filas = rows || []; this.loading = false; },
      error: () => { this.filas = []; this.loading = false; },
    });
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
