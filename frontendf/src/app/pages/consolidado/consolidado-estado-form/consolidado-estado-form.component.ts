import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { ConsolidadoResumenManual } from '../../../models/consolidado.model';

export interface ConsolidadoEstadoFormData {
  manual: ConsolidadoResumenManual;
}

@Component({
  selector: 'app-consolidado-estado-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './consolidado-estado-form.component.html',
  styleUrl: './consolidado-estado-form.component.css'
})
export class ConsolidadoEstadoFormComponent {
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<ConsolidadoEstadoFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConsolidadoEstadoFormData
  ) {
    const manual = data.manual || {
      faltas: 0,
      huecas: 0,
      apoyos: 0,
      capacitacion: 0,
      apertura_puesto: 0,
      servicios_temporales: 0,
      servicios_adicionales: 0,
      aprendiendo_consignas: 0,
      total: 0
    };

    this.form = this.fb.group({
      faltas: [manual.faltas ?? 0, [Validators.min(0)]],
      huecas: [manual.huecas ?? 0, [Validators.min(0)]],
      apoyos: [manual.apoyos ?? 0, [Validators.min(0)]],
      capacitacion: [manual.capacitacion ?? 0, [Validators.min(0)]],
      apertura_puesto: [manual.apertura_puesto ?? 0, [Validators.min(0)]],
      servicios_temporales: [manual.servicios_temporales ?? 0, [Validators.min(0)]],
      servicios_adicionales: [manual.servicios_adicionales ?? 0, [Validators.min(0)]],
      aprendiendo_consignas: [manual.aprendiendo_consignas ?? 0, [Validators.min(0)]]
    });
  }

  get total(): number {
    const v = this.form.value;
    return this.toInt(v.faltas) + this.toInt(v.huecas) + this.toInt(v.apoyos)
      + this.toInt(v.capacitacion) + this.toInt(v.apertura_puesto)
      + this.toInt(v.servicios_temporales) + this.toInt(v.servicios_adicionales)
      + this.toInt(v.aprendiendo_consignas);
  }

  cerrar(): void {
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.form.invalid) return;
    const v = this.form.value;
    this.dialogRef.close({
      faltas: this.toInt(v.faltas),
      huecas: this.toInt(v.huecas),
      apoyos: this.toInt(v.apoyos),
      capacitacion: this.toInt(v.capacitacion),
      apertura_puesto: this.toInt(v.apertura_puesto),
      servicios_temporales: this.toInt(v.servicios_temporales),
      servicios_adicionales: this.toInt(v.servicios_adicionales),
      aprendiendo_consignas: this.toInt(v.aprendiendo_consignas)
    });
  }

  private toInt(value: any): number {
    const num = Number(value);
    return Number.isFinite(num) ? Math.max(0, Math.trunc(num)) : 0;
  }
}
