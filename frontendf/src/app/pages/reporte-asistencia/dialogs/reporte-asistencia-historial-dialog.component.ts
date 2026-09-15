import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ReporteAsistenciaService } from '../../../services/reporte-asistencia.service';
import { ReporteAsistenciaHistorialItem } from '../../../models';

interface MesLite { anio: number; mes: number; label: string; }
interface PersonaPuesto { persona: string; meses: MesLite[]; desde: string; hasta: string; n_meses: number; }

@Component({
  selector: 'app-reporte-asistencia-historial-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule],
  templateUrl: './reporte-asistencia-historial-dialog.component.html'
})
export class ReporteAsistenciaHistorialDialogComponent implements OnInit {
  // Vista activa: 'mod' = Historial de Modificaciones (por defecto), 'puesto' = Historial por puesto.
  vista: 'mod' | 'puesto' = 'mod';

  // --- Modificaciones ---
  historial: ReporteAsistenciaHistorialItem[] = [];
  loading = true;
  error = '';

  // --- Por puesto ---
  puestoCargado = false;
  loadingPuesto = false;
  errorPuesto = '';
  cabecera = '';
  porPersona: PersonaPuesto[] = [];

  constructor(
    private reporteSvc: ReporteAsistenciaService,
    private dialogRef: MatDialogRef<ReporteAsistenciaHistorialDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { asignacionId: number; codigo?: string | null; fecha?: string | null }
  ) {}

  ngOnInit(): void {
    const id = this.data?.asignacionId;
    if (!id) {
      this.loading = false;
      this.error = 'No se encontro la asignacion.';
      return;
    }

    const params: any = {};
    if (this.data?.fecha) {
      params.fecha = this.data.fecha;
    }
    this.reporteSvc.getReporteAsistenciaHistorial(id, params).subscribe({
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

  setVista(v: 'mod' | 'puesto'): void {
    this.vista = v;
    if (v === 'puesto' && !this.puestoCargado) {
      this.cargarPuesto();
    }
  }

  cargarPuesto(): void {
    if (!this.data?.asignacionId) { return; }
    this.loadingPuesto = true;
    this.errorPuesto = '';
    this.reporteSvc.getHistorialPuesto(this.data.asignacionId).subscribe({
      next: (r: any) => {
        this.cabecera = [r?.codigo, r?.instalacion || r?.cliente, r?.puesto].filter(Boolean).join(' · ');
        this.porPersona = r?.por_persona || [];
        this.puestoCargado = true;
      },
      error: (err: any) => {
        console.error('Error al cargar historial del puesto', err);
        this.errorPuesto = 'No se pudo cargar el historial del puesto.';
      },
      complete: () => { this.loadingPuesto = false; }
    });
  }

  cerrar(): void {
    this.dialogRef.close();
  }
}
