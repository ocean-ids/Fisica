import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { InstalacionService } from '../../../services/instalacion.service';
import { Instalacion } from '../../../models';

@Component({
  selector: 'app-puesto-form',
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
  templateUrl: './puesto-form.component.html',
  styleUrl: './puesto-form.component.css'
})
export class PuestoFormComponent implements OnInit {
  puestoForm!: FormGroup;
  instalaciones: Instalacion[] = [];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PuestoFormComponent>,
    private instalacionService: InstalacionService,
    @Inject(MAT_DIALOG_DATA) public data: { puesto: any, clienteId: number }
  ) {}

  ngOnInit(): void {
    const puesto = this.data.puesto || {};
    this.puestoForm = this.fb.group({
      nombre: [puesto.nombre || '', Validators.required],
       cantidad_guardias: [puesto.cantidad_guardias || 1, [Validators.required, Validators.min(1)]],
      instalacion_id: [puesto.instalacion_id || null, Validators.required],
      horas_trabajo: [puesto.horas_trabajo || 8, Validators.required],
      turno_dia: [puesto.turno_dia || false],
      turno_noche: [puesto.turno_noche || false],
      dias: [puesto.dias || []]
    });

    
    this.instalacionService.getInstalaciones().subscribe({
      next: (data) => {
        this.instalaciones = data.filter(ins => (ins.cliente_id ?? ins.cliente) === this.data.clienteId);
      },
      error: (err) => console.error('Error al cargar instalaciones', err)
    });
  }

  onSubmit(): void {
    if (this.puestoForm.valid) {
      this.dialogRef.close(this.puestoForm.value);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
