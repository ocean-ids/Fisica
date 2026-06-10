import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

export interface VacanteItem {
  id: number;
  codigo: string;
  cliente: string;
  instalacion: string;
  puesto: string;
  canton: string;
  canton_id: number | null;
  horario: string;
}

export interface VacantesModalData {
  vacantes: VacanteItem[];
  mesLabel: string;
}

@Component({
  selector: 'app-vacantes-modal',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>
      Puestos sin persona
      <span class="badge bg-danger ms-2">{{ data.vacantes.length }}</span>
    </h2>
    <mat-dialog-content>
      @if (data.mesLabel) {
        <div class="text-muted mb-2">{{ data.mesLabel }} — clic en una fila para asignar persona</div>
      }

      @if (!data.vacantes.length) {
        <div class="text-muted text-center py-3">No hay puestos vacantes este mes. 🎉</div>
      } @else {
        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle">
            <thead class="table-light">
              <tr>
                <th>Nominativo</th>
                <th>Cliente</th>
                <th>Puesto</th>
                <th>Cantón</th>
                <th>Horario</th>
              </tr>
            </thead>
            <tbody>
              @for (v of data.vacantes; track v.id) {
                <tr (click)="seleccionar(v)" style="cursor: pointer;">
                  <td>{{ v.codigo || '-' }}</td>
                  <td>{{ v.cliente || '-' }}</td>
                  <td>{{ v.puesto || '-' }}</td>
                  <td>{{ v.canton || '-' }}</td>
                  <td>{{ v.horario || '-' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-stroked-button mat-dialog-close>Cerrar</button>
    </mat-dialog-actions>
  `,
})
export class VacantesModalComponent {
  constructor(
    @Inject(MAT_DIALOG_DATA) public data: VacantesModalData,
    private dialogRef: MatDialogRef<VacantesModalComponent, VacanteItem>
  ) {}

  seleccionar(v: VacanteItem): void {
    this.dialogRef.close(v);
  }
}
