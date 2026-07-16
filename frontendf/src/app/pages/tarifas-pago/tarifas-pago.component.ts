import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { ReportePagoService } from '../../services/reporte-pago.service';
import { TarifaPago } from '../../models/reporte-pago.model';
import { TarifaPagoDialogComponent } from './tarifa-pago-dialog/tarifa-pago-dialog.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-tarifas-pago',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './tarifas-pago.component.html',
  styleUrl: './tarifas-pago.component.css',
})
export class TarifasPagoComponent implements OnInit {
  tarifas: TarifaPago[] = [];
  loading = false;

  constructor(private srv: ReportePagoService, private dialog: MatDialog) {}

  ngOnInit(): void { this.cargar(); }

  cargar(): void {
    this.loading = true;
    this.srv.listarTarifas().subscribe({
      next: (t) => { this.tarifas = t || []; this.loading = false; },
      error: () => { this.tarifas = []; this.loading = false; },
    });
  }

  get tipos(): string[] {
    const out: string[] = [];
    for (const t of this.tarifas) { if (!out.includes(t.tipo_servicio)) { out.push(t.tipo_servicio); } }
    return out;
  }

  nueva(): void { this.abrir(null); }
  editar(t: TarifaPago): void { this.abrir(t); }

  private abrir(row: TarifaPago | null): void {
    const ref = this.dialog.open(TarifaPagoDialogComponent, {
      width: '480px', maxWidth: '95vw',
      data: { row: row || undefined, tipos: this.tipos },
    });
    ref.afterClosed().subscribe((res) => {
      if (!res) { return; }
      const ok = () => { this.cargar(); Swal.fire({ icon: 'success', title: 'Tarifa guardada', toast: true, position: 'top-end', showConfirmButton: false, timer: 1200 }); };
      const fail = () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo guardar (¿banda repetida?)' });
      if (row?.id) {
        this.srv.actualizarTarifa(row.id, res).subscribe({ next: ok, error: fail });
      } else {
        this.srv.crearTarifa(res).subscribe({ next: ok, error: fail });
      }
    });
  }

  eliminar(t: TarifaPago): void {
    if (!t.id) { return; }
    Swal.fire({
      title: '¿Eliminar tarifa?',
      text: `${t.tipo_servicio} ${t.horas_min}-${t.horas_max}h`,
      icon: 'warning', showCancelButton: true, confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar',
    }).then((r) => {
      if (r.isConfirmed) {
        this.srv.eliminarTarifa(t.id!).subscribe({ next: () => this.cargar(), error: () => this.cargar() });
      }
    });
  }

  num(v: any): number { return Number(v || 0); }
}
