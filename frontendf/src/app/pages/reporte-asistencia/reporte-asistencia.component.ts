import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ReporteAsistenciaService } from '../../services/reporte-asistencia.service';
import { ReporteAsistenciaEditDialogComponent } from './reporte-asistencia-edit-dialog.component';
import { ReporteAsistenciaRow } from '../../models';
import { ReporteAsistenciaColorDialogComponent } from './reporte-asistencia-color-dialog.component';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { PersonaService } from '../../services/persona.service';
import { PersonaFormComponent } from '../personas/persona-form/persona-form.component';

@Component({
  selector: 'app-reporte-asistencia',
  standalone: true,
  imports: [CommonModule, MatButtonModule, FormsModule, MatButtonToggleModule],
  templateUrl: './reporte-asistencia.component.html',
  styleUrl: './reporte-asistencia.component.css'
})
export class ReporteAsistenciaComponent implements OnInit {
  reporte: ReporteAsistenciaRow[] = [];
  loading = false;
  filtroFecha = '';
  filtroClienteId = '';
  filtroFechaDisplay = '';
  filtroTurno = '';
  readonly colorPalette: {name: string, value: string}[] = [
    { name: 'Amarillo', value: '#fff8b3' },
    { name: 'Rojo', value: '#ffb3b3' },
    { name: 'Verde', value: '#b3ffb3' },
    { name: 'Azul', value: '#b3d9ff' },
    { name: 'Naranja', value: '#ffd9b3' },
    { name: 'Verde Lima', value: '#2ff968' },
    { name: 'Gris', value: '#d9d9d9' },
    { name: 'Celeste', value: '#b3e6ff' },
    { name: 'Rosa', value: '#ffb3e6' },
    { name: 'Beige', value: '#f5f5dc' },
    { name: 'Lima', value: '#d9ffb3' },
    { name: 'Turquesa', value: '#b3fff0' },
    { name: 'Lavanda', value: '#e6b3ff' },
    { name: 'Mostaza', value: '#ffdb58' },
    { name: 'Coral', value: '#ff7f50' },
    { name: 'Cian', value: '#00ffff' },
    { name: 'Crema', value: '#fffdd0' },
    { name: 'Caqui', value: '#f0e68c' },
    { name: 'Salmón', value: '#fa8072' },
    { name: 'Blanco', value: '#ffffff' },
  ];

  constructor(
    private reporteSvc: ReporteAsistenciaService,
    private dialog: MatDialog,
    private personaService: PersonaService
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

  onRowDoubleClick(row: ReporteAsistenciaRow): void {
    if (!row?.asignacion_id) return;

    const dialogRef = this.dialog.open(ReporteAsistenciaColorDialogComponent, {
      width: '420px',
      maxWidth: '95vw',
      data: {
        selectedColor: row.row_color || this.colorPalette[0].value,
        palette: this.colorPalette
      }
    });

    dialogRef.afterClosed().subscribe((selectedColor?: string) => {
      if (!selectedColor || !row.asignacion_id) return;

      const payload = {
        row_color: selectedColor
      };

      this.reporteSvc.updateReporteAsistencia(row.asignacion_id, payload).subscribe({
        next: (res) => {
          row.row_color = res.row_color || selectedColor;
        },
        error: (err) => console.error('Error al actualizar color de fila:', err)
      });
    });
  }

  getRowColor(row: ReporteAsistenciaRow): string {
    return row.row_color || '';
  }


  abrirModalNuevaPersona(): void {
      const dialogRef = this.dialog.open(PersonaFormComponent, {
        width: '600px',
        data: {}
      });

      dialogRef.afterClosed().subscribe(result => {
        if (!result) return;
        this.personaService.createPersona(result).subscribe({
          next: () => {
            this.cargarReporte();
          },
          error: (err) => console.error('Error al crear persona:', err)
        });
      });
  }

  descargarExcel(): void {
    const params: any = {};
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroClienteId) params.cliente_id = this.filtroClienteId;
    if (this.filtroTurno) params. turno = this.filtroTurno;
    this.reporteSvc.exportarExcel(params).subscribe({
      next: (blog) => this.descargarArchivo(blog, `reporte_asistencia_${this.filtroFecha}.xlsx`),
      error: (err) => console.error("Error al descargar el excel", err)
    });
  }

  descargarPdf(): void {
    const params: any = {};
    if(this.filtroFecha) params.fecha = this.filtroFecha;
    if(this.filtroClienteId) params.cliente_id = this.filtroClienteId;
    if(this.filtroTurno) params.turno = this.filtroTurno;
    this.reporteSvc.exportarPdf(params).subscribe({
      next: (blog) => this.descargarArchivo(blog, `reporte_asistencia_${this.filtroFecha}.pdf`),
      error: (err) => console.error("Error al descargar el pdf", err)
    })
  }



  private descargarArchivo(blob: Blob, nombre: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  cargarReporte(): void {
    const params: any = {};
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroClienteId) params.cliente_id = this.filtroClienteId;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    this.loading = true;
    this.reporteSvc.getReporteAsistencia(params).subscribe({
      next: data=> this.reporte = data || [],
      error: err => console.error('Error al cargar reporte de asistencia:', err),
      complete: () => this.loading = false
    });
  }

  abrirModalEdicion(row: ReporteAsistenciaRow): void {
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
      row.reemplazo_id = res.reemplazo_id;
      row.reemplazo = res.reemplazo;
      row.modificado_por = res.modificado_por;
      row.modificado_en = res.modificado_en;
    });
  }

  limpiarFiltros(): void {
    this.setHoy();
    this.filtroClienteId = '';
    this.filtroTurno = '';
    this.cargarReporte();
  }

  onFechaChange(event: Event): void {
    const iso = (event.target as HTMLInputElement).value;
    this.filtroFecha = iso || '';
    this.filtroFechaDisplay = iso ? iso.split('-').reverse().join('/') : '';
    this.cargarReporte();
  }
  

  estadoClass(estado?: string): string {
    return estado === 'ADICIONAL' ? 'badge bg-danger' : 'badge bg-success';
  }
}
