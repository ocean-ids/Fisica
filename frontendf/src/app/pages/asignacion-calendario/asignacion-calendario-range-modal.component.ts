import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

export interface AsignacionRangeModalData {
  start: string;
  end: string;
  seq: string;
  isSacafranco: boolean;
}

export interface AsignacionRangeModalResult {
  start: string;
  end: string;
  seq: string;
}

@Component({
  selector: 'app-asignacion-calendario-range-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './asignacion-calendario-range-modal.component.html',
  styleUrl: './asignacion-calendario-range-modal.component.css'
})
export class AsignacionCalendarioRangeModalComponent {
  start: string;
  end: string;
  seq: string;
  errorText: string = '';

  constructor(
    private dialogRef: MatDialogRef<AsignacionCalendarioRangeModalComponent, AsignacionRangeModalResult>,
    @Inject(MAT_DIALOG_DATA) public data: AsignacionRangeModalData
  ) {
    this.start = data.start || '';
    this.end = data.end || '';
    this.seq = data.seq || '';
  }

  cancel(): void {
    this.dialogRef.close();
  }

  submit(): void {
    this.errorText = '';
    if (!this.start || !this.end || !this.seq) {
      this.errorText = 'Completa desde, hasta y secuencia.';
      return;
    }

    const startDate = new Date(this.start + 'T00:00:00');
    const endDate = new Date(this.end + 'T00:00:00');
    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
      this.errorText = 'Fechas inválidas.';
      return;
    }
    if (startDate > endDate) {
      this.errorText = 'La fecha final debe ser mayor o igual a la inicial.';
      return;
    }

    const currentYear = new Date().getFullYear();
    if (startDate.getFullYear() !== currentYear || endDate.getFullYear() !== currentYear) {
      this.errorText = 'El rango debe estar dentro del año actual.';
      return;
    }

    if (!this.isValidSequence(this.seq, this.data.isSacafranco)) {
      this.errorText = this.data.isSacafranco
        ? 'Ingresa una secuencia válida.'
        : 'Solo se permiten F, D o N.';
      return;
    }

    this.dialogRef.close({
      start: this.start,
      end: this.end,
      seq: this.seq
    });
  }

  private isValidSequence(seq: string, isSacafranco: boolean): boolean {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return false;
    if (isSacafranco) return true;
    return /[FDN]/.test(raw);
  }
}
