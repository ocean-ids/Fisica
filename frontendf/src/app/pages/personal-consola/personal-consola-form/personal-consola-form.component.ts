import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { PersonalConsola } from '../../../models';

@Component({
  selector: 'app-personal-consola-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule
  ],
  templateUrl: './personal-consola-form.component.html',
  styleUrl: './personal-consola-form.component.css'
})
export class PersonalConsolaFormComponent implements OnInit{

  form!: FormGroup;

  turnos = ['Diurno', 'Nocturno'];
  tipos = ['SUPERVISOR', 'OPERADOR', 'OCEAN SECURITY'];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PersonalConsolaFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: PersonalConsola
  ){}

  ngOnInit(): void {
    this.form = this.fb.group({
      turno: [this.data?.turno || '', Validators.required],
      cedula: [this.data?.cedula || ''],
      nombres: [this.data?.nombres || '', Validators.required],
      apellidos: [this.data?.apellidos || '', Validators.required],
      tipo: [this.data?.tipo || '', Validators.required]
    });
  }

  cancelar(): void {
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.form.invalid) return;
    this.dialogRef.close(this.form.value);
  }
}
