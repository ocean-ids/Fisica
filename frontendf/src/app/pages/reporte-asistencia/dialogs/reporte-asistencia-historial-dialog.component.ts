import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ReporteAsistenciaService } from '../../../services/reporte-asistencia.service';
import { ReporteAsistenciaHistorialItem } from '../../../models';

@Component({
  selector: 'app-reporte-asistencia-historial-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  templateUrl: './reporte-asistencia-historial-dialog.component.html'
})
export class ReporteAsistenciaHistorialDialogComponent implements OnInit {
  historial: ReporteAsistenciaHistorialItem[] = [];
  loading = true;
  error = '';

  constructor(
    private reporteSvc: ReporteAsistenciaService,
    private dialogRef: MatDialogRef<ReporteAsistenciaHistorialDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { asignacionId: number; codigo?: string | null }
  ) {}

  ngOnInit(): void {
    const id = this.data?.asignacionId;
    if (!id) {
      this.loading = false;
      this.error = 'No se encontro la asignacion.';
      return;
    }

    this.reporteSvc.getReporteAsistenciaHistorial(id).subscribe({
      next: (items) => {
        this.historial = items || [];
      },
      error: (err) => {
        console.error('Error al cargar historial', err);
        this.error = 'No se pudo cargar el historial.';
      },
      complete: () => {
        this.loading = false;
      }
    });
  }

  cerrar(): void {
    this.dialogRef.close();
  }
}
