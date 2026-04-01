import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import Swal from 'sweetalert2';
import { ConsolidadoService } from '../../services/consolidado.service';
import { ConsolidadoRow } from '../../models/consolidado.model';
import { ConsolidadoObservacionDialogComponent } from './consolidado-observacion-dialog/consolidado-observacion-dialog.component';

@Component({
  selector: 'app-consolidado',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonToggleModule, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './consolidado.component.html',
  styleUrl: './consolidado.component.css'
})
export class ConsolidadoComponent implements OnInit {
  lista: ConsolidadoRow[] = [];
  agrupado: { label: string; rows: ConsolidadoRow[] }[] = [];
  filtroFecha = '';
  filtroTurno = '';
  loading = false;

  constructor(
    private svc: ConsolidadoService,
    private dialog: MatDialog
  ) {}

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
        this.agrupado = this.buildAgrupado();
        this.loading = false;
      },
      error: err => {
        console.error('Error al cargar consolidado:', err);
        this.loading = false;
      }
    });
  }

  private buildAgrupado(): { label: string; rows: ConsolidadoRow[] }[] {
    const consola = this.lista.filter(r => r.tipo === 'CONSOLa');
    const guardias = this.lista.filter(r => r.tipo !== 'CONSOLa');

    const zonas: Record<string, ConsolidadoRow[]> = {};
    for (const row of guardias) {
      const zona = (row.zona || '').trim() || 'SIN ZONA';
      if (!zonas[zona]) zonas[zona] = [];
      zonas[zona].push(row);
    }

    const result: { label: string; rows: ConsolidadoRow[] }[] = [];
    if (consola.length) {
      result.push({ label: 'PERSONAL DE CONSOLA Y OFICINAS', rows: consola });
    }

    for (const zona of Object.keys(zonas).sort()) {
      result.push({ label: zona.toUpperCase(), rows: zonas[zona] });
    }

    return result;
  }

  abrirObservacion(row: ConsolidadoRow): void {
    const dialogRef = this.dialog.open(ConsolidadoObservacionDialogComponent, {
      width: '640px',
      data: { row }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;
      row.observacion = result.observacion || '';
      if (row.tipo === 'CONSOLa') {
        row.nominativo = result.nominativo || '';
        row.proyecto = result.proyecto || '';
      }
      this.guardarObservacion(row);
    });
  }

  private guardarObservacion(row: ConsolidadoRow): void {
    if (!row.referencia_id || !row.tipo) return;

    const payload = {
      fecha: row.fecha || this.filtroFecha,
      turno: row.turno || this.filtroTurno,
      tipo: row.tipo,
      referencia_id: row.referencia_id,
      nominativo: row.nominativo || '',
      proyecto: row.proyecto || '',
      observacion: row.observacion || ''
    };

    if (row.consolidado_id) {
      this.svc.updateConsolidado(row.consolidado_id, {
        observacion: payload.observacion,
        nominativo: payload.nominativo,
        proyecto: payload.proyecto
      }).subscribe({
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

  getNombreCompleto(row: ConsolidadoRow): string {
    const apellidos = (row.apellidos || '').trim();
    const nombres = (row.nombres || '').trim();
    const full = `${apellidos} ${nombres}`.trim();
    return full || '-';
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
