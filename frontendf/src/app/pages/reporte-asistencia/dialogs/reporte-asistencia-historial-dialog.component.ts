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
  // Sacafranco: puestos/nominativos que ha cubierto (con fechas).
  porPuestoSaca: Array<{ cliente: string; puesto: string; turno: string; desde: string; hasta: string; dias: number }> = [];

  constructor(
    private reporteSvc: ReporteAsistenciaService,
    private dialogRef: MatDialogRef<ReporteAsistenciaHistorialDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { asignacionId?: number; sacafrancoFilaId?: number; codigo?: string | null; fecha?: string | null }
  ) {}

  ngOnInit(): void {
    const asigId = this.data?.asignacionId;
    const sacaId = this.data?.sacafrancoFilaId;
    if (!asigId && !sacaId) {
      this.loading = false;
      this.error = 'No se encontro el registro.';
      return;
    }

    const params: any = {};
    if (this.data?.fecha) {
      params.fecha = this.data.fecha;
    }
    const obs = sacaId
      ? this.reporteSvc.getSacafrancoHistorial(sacaId, params)
      : this.reporteSvc.getReporteAsistenciaHistorial(asigId!, params);
    obs.subscribe({
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
    this.loadingPuesto = true;
    this.errorPuesto = '';

    // Sacafranco: "Por puesto" = puestos que ha cubierto (no tiene puesto/asignación fija).
    if (this.esSacafranco) {
      this.reporteSvc.getHistorialPuestoSacafranco(this.data.sacafrancoFilaId!).subscribe({
        next: (r: any) => {
          this.cabecera = r?.cabecera || '';
          this.porPuestoSaca = r?.por_puesto || [];
          this.puestoCargado = true;
        },
        error: (err: any) => {
          console.error('Error al cargar puestos cubiertos del sacafranco', err);
          this.errorPuesto = 'No se pudo cargar los puestos cubiertos.';
        },
        complete: () => { this.loadingPuesto = false; }
      });
      return;
    }

    if (!this.data?.asignacionId) { this.loadingPuesto = false; return; }
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

  // La vista "Por puesto" no aplica a sacafranco (no tiene asignación/puesto propio).
  get esSacafranco(): boolean {
    return !!this.data?.sacafrancoFilaId && !this.data?.asignacionId;
  }

  cerrar(): void {
    this.dialogRef.close();
  }
}
