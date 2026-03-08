import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ReporteAsistenciaService } from '../../services/reporte-asistencia.service';
import { ReporteAsistenciaEditDialogComponent } from './reporte-asistencia-edit-dialog.component';

@Component({
  selector: 'app-reporte-asistencia',
  standalone: true,
  imports: [CommonModule, MatButtonModule],
  templateUrl: './reporte-asistencia.component.html',
  styleUrl: './reporte-asistencia.component.css'
})
export class ReporteAsistenciaComponent implements OnInit {
  reporte: any[] = [];
  loading = false;
  filtroFecha = '';
  filtroClienteId = '';
  filtroFechaDisplay = '';

  constructor(
    private reporteSvc: ReporteAsistenciaService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.setHoy();
    this.cargarReporte();
  }

  private setHoy(): void {
    const hoy = new Date();
    const isoLocal = new Date(hoy.getTime() - hoy.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
    this.filtroFecha = isoLocal;
    this.filtroFechaDisplay = isoLocal.split('-').reverse().join('/');
  }

  cargarReporte(): void {
    const params: any = {};
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroClienteId) params.cliente_id = this.filtroClienteId;
    this.loading = true;
    this.reporteSvc.getReporteAsistencia(params).subscribe({
      next: data=> this.reporte = data || [],
      error: err => console.error('Error al cargar reporte de asistencia:', err),
      complete: () => this.loading = false
    })
  }

  abrirModalEdicion(row: any): void {
    if (!row?.asignacion_id) return;

    const dialogRef = this.dialog.open(ReporteAsistenciaEditDialogComponent, {
      width: '700px',
      maxWidth: '95vw',
      data: { row: { ...row } }
    });

    dialogRef.afterClosed().subscribe((res) => {
      if (!res) return;
      row.codigo = res.codigo;
      row.estado = res.estado;
      row.descripcion = res.descripcion;
      row.modificado_por = res.modificado_por;
      row.modificado_en = res.modificado_en;
    });
  }

  limpiarFiltros(): void {
    this.setHoy();
    this.filtroClienteId = '';
    this.cargarReporte();
  }

  onFechaChange(event: Event): void {
    const iso = (event.target as HTMLInputElement).value;
    this.filtroFecha = iso || '';
    this.filtroFechaDisplay = iso ? iso.split('-').reverse().join('/') : '';
    this.cargarReporte();
  }


  estadoClass(estado: string): string {
    return estado === 'ADICIONAL' ? 'badge bg-danger' : 'badge bg-success';
  }
}
