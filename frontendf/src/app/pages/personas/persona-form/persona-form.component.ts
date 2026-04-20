import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { Persona } from '../../../models/persona.model';

@Component({
  selector: 'app-persona-form',
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
  templateUrl: './persona-form.component.html',
  styleUrl: './persona-form.component.css'
})
export class PersonaFormComponent implements OnInit {
  personaForm!: FormGroup;
  tipos: Persona['tipo'][] = [
    'FIJOS',
    'RETENES',
    'CUSTODIO',
    'EVENTUALES',
    'SACAFRANCO',
    'SACAVACACIONES',
    'SUPERVISOR ZONAL',
    'SUPERVISOR MOTORIZADO'
  ];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PersonaFormComponent>,
    @Inject(MAT_DIALOG_DATA) public persona: Persona
  ) {}

  ngOnInit(): void {
    this.personaForm = this.fb.group({
      nombres: [this.persona?.nombres || '', Validators.required],
      apellidos: [this.persona?.apellidos || '', Validators.required],
      cedula: [this.persona?.cedula || '', [Validators.required, Validators.pattern('^[0-9]{1,10}$'), Validators.maxLength(10)]],
      tipo: [this.persona?.tipo ?? 'FIJOS', Validators.required]
    });
  }

  onSubmit(): void {
    if (this.personaForm.valid) {
      this.dialogRef.close(this.personaForm.value);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
