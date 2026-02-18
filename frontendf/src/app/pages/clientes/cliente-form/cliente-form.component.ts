import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { Cliente } from '../../../models/cliente.model';
import { MatSelectModule } from '@angular/material/select';



@Component({
  selector: 'app-cliente-form',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule, 
    MatSelectModule
  ],
  templateUrl: './cliente-form.component.html',
  styleUrl: './cliente-form.component.css'
})
export class ClienteFormComponent implements OnInit {
  clienteForm!: FormGroup;
  
   constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<ClienteFormComponent>,
    @Inject(MAT_DIALOG_DATA) public cliente: Cliente
  ) {}

  ngOnInit(): void {
    this.clienteForm = this.fb.group({
      razon_social: [this.cliente?.razon_social || '', Validators.required],
      nombre_comercial: [this.cliente?.nombre_comercial || '', Validators.required],
      ruc: [this.cliente?.ruc || '', [
        Validators.pattern(/^\d{10}(\d{3})?$/),
        Validators.minLength(10),
        Validators.maxLength(13)
      ]],
      size: [this.cliente?.size || 'PEQUEÑO', Validators.required]
    });
  }

  onSubmit(): void {
    if (this.clienteForm.valid){
      this.dialogRef.close(this.clienteForm.value);
    }
  }
}
  