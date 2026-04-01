import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { ConsolidadoRow } from '../../../models/consolidado.model';

export interface ConsolidadoObservacionDialogData {
  row: ConsolidadoRow;
}

@Component({
  selector: 'app-consolidado-observacion-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './consolidado-observacion-dialog.component.html',
  styleUrl: './consolidado-observacion-dialog.component.css'
})
export class ConsolidadoObservacionDialogComponent {
  form: FormGroup;
  isConsola: boolean;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<ConsolidadoObservacionDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConsolidadoObservacionDialogData
  ) {
    const tipo = (data.row?.tipo || '').toString().toUpperCase();
    this.isConsola = tipo.startsWith('CONS');
    this.form = this.fb.group({
      nominativo: [data.row?.nominativo || '', Validators.maxLength(50)],
      proyecto: [data.row?.proyecto || '', Validators.maxLength(120)],
      observacion: [data.row?.observacion || '', Validators.maxLength(200)]
    });
  }

  cerrar(): void {
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.form.invalid) return;
    this.dialogRef.close({
      nominativo: this.form.value.nominativo || '',
      proyecto: this.form.value.proyecto || '',
      observacion: this.form.value.observacion || ''
    });
  }
}
