import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { ConsolidadoRow } from '../../../models/consolidado.model';

export interface ConsolidadoFormDialogData {
  row: ConsolidadoRow;
}

@Component({
  selector: 'app-consolidado-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './consolidado-form.component.html',
  styleUrl: './consolidado-form.component.css'
})
export class ConsolidadoFormComponent {
  form: FormGroup;
  isConsola: boolean;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<ConsolidadoFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConsolidadoFormDialogData
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
