import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import Swal from 'sweetalert2';
import { TarifaPago } from '../../../models/reporte-pago.model';

interface DialogData {
  row?: TarifaPago;      // presente = edición
  tipos?: string[];      // tipos existentes (para sugerencias)
}

@Component({
  selector: 'app-tarifa-pago-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule],
  templateUrl: './tarifa-pago-dialog.component.html',
  styleUrl: './tarifa-pago-dialog.component.css',
})
export class TarifaPagoDialogComponent {
  row: TarifaPago;
  esEdicion: boolean;
  tipos: string[];

  constructor(
    private ref: MatDialogRef<TarifaPagoDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
  ) {
    this.esEdicion = !!data?.row?.id;
    this.row = data?.row
      ? { ...data.row }
      : { tipo_servicio: '', horas_min: 1, horas_max: 3, valor: 0 };
    this.tipos = data?.tipos || [];
  }

  guardar(): void {
    if (!this.row.tipo_servicio.trim()) {
      Swal.fire({ icon: 'warning', title: 'Falta el tipo de servicio' });
      return;
    }
    if (Number(this.row.horas_min) > Number(this.row.horas_max)) {
      Swal.fire({ icon: 'warning', title: 'El rango de horas es inválido' });
      return;
    }
    this.ref.close({
      tipo_servicio: this.row.tipo_servicio.trim(),
      horas_min: this.row.horas_min,
      horas_max: this.row.horas_max,
      valor: this.row.valor,
    });
  }

  cancelar(): void { this.ref.close(); }
}
