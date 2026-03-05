import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReporteAsistenciaService } from '../../services/reporte-asistencia.service';

@Component({
  selector: 'app-reporte-asistencia',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reporte-asistencia.component.html',
  styleUrl: './reporte-asistencia.component.css'
})
export class ReporteAsistenciaComponent implements OnInit {
  reporte: any[] = [];
  loading = false;
  filtroFecha = '';
  filtroClienteId = '';

  constructor(private reporteSvc: ReporteAsistenciaService) {}

  ngOnInit(): void {
    this.cargarReporte();
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
  limpiarFiltros(): void {
    this.filtroFecha = '';
    this.filtroClienteId = '';
    this.cargarReporte();
  }


  estadoClass(estado: string): string {
    return estado === 'ADICIONAL' ? 'badge bg-danger' : 'badge bg-success';
  }
}
