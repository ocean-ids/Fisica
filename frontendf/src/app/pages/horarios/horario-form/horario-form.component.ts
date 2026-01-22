import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-horario-form',
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
  templateUrl: './horario-form.component.html',
  styleUrl: './horario-form.component.css'
})
export class HorarioFormComponent implements OnInit {
  horarioForm!: FormGroup;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<HorarioFormComponent>,
    @Inject(MAT_DIALOG_DATA) public horario: any
  ) {}

  ngOnInit(): void {
    this.horarioForm = this.fb.group({
      denominativo: [this.horario?.denominativo || '', Validators.required],
      hora_ingreso: [this.horario?.hora_ingreso || '', Validators.required],
      hora_salida: [this.horario?.hora_salida || '', Validators.required]
    });
  }

  onSubmit(): void {
    if (this.horarioForm.valid) {
      this.dialogRef.close(this.horarioForm.value);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
