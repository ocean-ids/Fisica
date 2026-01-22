import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { Cliente } from '../../../models/cliente.model';

@Component({
  selector: 'app-instalacion-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule
  ],
  templateUrl: './instalacion-form.component.html',
  styleUrl: './instalacion-form.component.css'
})
export class InstalacionFormComponent implements OnInit {
  instalacionForm!: FormGroup;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<InstalacionFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { instalacion: any, clientes: Cliente[] }
  ) {}

  ngOnInit(): void {
    const instalacion = this.data.instalacion || {};
    this.instalacionForm = this.fb.group({
      cliente_id: [instalacion.cliente_id || '', Validators.required],
      provincia: [instalacion.provincia || '', Validators.required],
      ciudad: [instalacion.ciudad || '', Validators.required]
    });
  }

  onSubmit(): void {
    if (this.instalacionForm.valid) {
      this.dialogRef.close(this.instalacionForm.value);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
