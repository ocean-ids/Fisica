import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { HorarioService } from '../../../services/horario.service';

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
  patrones: any[] = [];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<HorarioFormComponent>,
    @Inject(MAT_DIALOG_DATA) public horario: any,
    private horarioService: HorarioService,
  ) {}

  ngOnInit(): void {
    this.horarioForm = this.fb.group({
      hora_ingreso: [this.horario?.hora_ingreso || null, Validators.required],
      hora_salida: [this.horario?.hora_salida || null, Validators.required],
      patron_id: [this.horario?.patronHorario?.id || null],
    });

    this.cargarPatrones();
  }

  private cargarPatrones(): void {
    this.horarioService.obtenerPatrones().subscribe({
      next: (data) => (this.patrones = data || []),
      error: (err) => console.error('Error al cargar patrones', err),
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
