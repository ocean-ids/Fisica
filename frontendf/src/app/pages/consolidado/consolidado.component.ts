import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import Swal from 'sweetalert2';
import { ConsolidadoService } from '../../services/consolidado.service';
import { ConsolidadoRow } from '../../models/consolidado.model';

@Component({
  selector: 'app-consolidado',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonToggleModule],
  templateUrl: './consolidado.component.html',
  styleUrl: './consolidado.component.css'
})
export class ConsolidadoComponent implements OnInit {
  lista: ConsolidadoRow[] = [];
  filtroFecha = '';
  filtroTurno = '';
  loading = false;

  constructor(private svc: ConsolidadoService) {}

  ngOnInit(): void {
    this.setHoy();
    this.filtroTurno = 'Diurno';
    this.cargar();
  }

  onFechaChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.filtroFecha = input.value;
    this.cargar();
  }

  cargar(): void {
    const params: any = {};
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    this.loading = true;
    this.svc.getConsolidadoArmado(params).subscribe({
      next: data => {
        this.lista = data || [];
        this.loading = false;
      },
      error: err => {
        console.error('Error al cargar consolidado:', err);
        this.loading = false;
      }
    });
  }

  guardarObservacion(row: ConsolidadoRow): void {
    if (!row.referencia_id || !row.tipo) return;

    const payload = {
      fecha: row.fecha || this.filtroFecha,
      turno: row.turno || this.filtroTurno,
      tipo: row.tipo,
      referencia_id: row.referencia_id,
      observacion: row.observacion || ''
    };

    if (row.consolidado_id) {
      this.svc.updateConsolidado(row.consolidado_id, { observacion: payload.observacion }).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Observacion guardada', timer: 1200, showConfirmButton: false });
        },
        error: () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo guardar' })
      });
      return;
    }

    if (!payload.fecha || !payload.turno) {
      Swal.fire({ icon: 'warning', title: 'Falta fecha o turno' });
      return;
    }

    this.svc.createConsolidado(payload).subscribe({
      next: (res: any) => {
        row.consolidado_id = res?.id;
        Swal.fire({ icon: 'success', title: 'Observacion guardada', timer: 1200, showConfirmButton: false });
      },
      error: () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo guardar' })
    });
  }

  descargarExcel(): void {
    const params: any = {};
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    this.svc.exportarExcel(params).subscribe({
      next: (blob: Blob) => this.descargarArchivo(blob, `consolidado_${this.filtroFecha || 'hoy'}.xlsx`),
      error: (err) => console.error('Error al descargar excel:', err)
    });
  }

  descargarPdf(): void {
    const params: any = {};
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    this.svc.exportarPdf(params).subscribe({
      next: (blob: Blob) => this.descargarArchivo(blob, `consolidado_${this.filtroFecha || 'hoy'}.pdf`),
      error: (err) => console.error('Error al descargar pdf:', err)
    });
  }

  private descargarArchivo(blob: Blob, nombre: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  private setHoy(): void {
    const hoy = new Date();
    const isoLocal = new Date(hoy.getTime() - hoy.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
    this.filtroFecha = isoLocal;
  }
}
