import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
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
    MatSelectModule,
    MatIconModule
  ],
  templateUrl: './puesto-form.component.html',
  styleUrl: './puesto-form.component.css'
})
export class PuestoFormComponent implements OnInit {
  puestoForm!: FormGroup;
  instalaciones: Instalacion[] = [];
  hoursOptions: number[] = Array.from({length:24}, (_,i) => i+1);

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PuestoFormComponent>,
    private instalacionService: InstalacionService,
    @Inject(MAT_DIALOG_DATA) public data: { puesto: any, clienteId: number }
  ) {}

  ngOnInit(): void {
    const puesto = this.data.puesto || {};
    this.puestoForm = this.fb.group({
      nombre: [puesto?.nombre || '', Validators.required],
      instalacion_id: [puesto?.instalacion_id || '', Validators.required],
      cantidad_guardias: [puesto?.cantidad_guardias ?? 1, Validators.required],
      descripcion_sistema: [puesto?.descripcion_sistema || ''],
      horarios: this.fb.array([])
    });

    // initialize horarios from existing puesto or a single empty horario
    const initialHorarios = puesto?.horarios && Array.isArray(puesto.horarios) ? puesto.horarios : [];
    if (initialHorarios.length) {
      for (const h of initialHorarios) {
        this.addHorario(h.horas ?? 12, h.turno || 'Diurno', h.dia ? [h.dia] : []);
      }
    } else {
      this.addHorario(12, 'Diurno', []);
    }

    this.instalacionService.getInstalaciones().subscribe({
      next: (data) => {
        this.instalaciones = data.filter(ins => (ins.cliente_id ?? ins.cliente) === this.data.clienteId);
      },
      error: (err) => console.error('Error al cargar instalaciones', err)
    });
  }

  private normalizeTurno(value: any): string | null {
    if (!value && value !== '') return null;
    const v = String(value).trim().toLowerCase();
    if (!v) return null;
    if (v.startsWith('n')) return 'Nocturno';
    if (v.startsWith('d')) return 'Diurno';
    // fallback: if already Diurno/Nocturno return as-is with capitalization
    if (v.includes('noct')) return 'Nocturno';
    if (v.includes('diurn')) return 'Diurno';
    return null;
  }

  onSubmit(): void {
    if (this.puestoForm.valid) {
      const formValue = this.puestoForm.value;
      const selectedInstalacion = this.instalaciones.find(i => i.id === formValue.instalacion_id);
      // build horarios payload: expand checked days into one object per day
      const horariosPayload: any[] = [];
      const horariosFA = this.puestoForm.get('horarios') as any;
      for (let i = 0; i < horariosFA.length; i++) {
        const h = horariosFA.at(i).value;
        const days: number[] = h.days || [];
        if (days.length) {
          for (const d of days) {
            horariosPayload.push({ dia: d, horas: h.horas, turno: h.turno });
          }
        }
      }

      const payload: any = {
        ...formValue,
        horarios: horariosPayload,
        instalacion_nombre: selectedInstalacion?.nombre || selectedInstalacion?.codigo || null
      };
      console.log('Payload enviado:', JSON.stringify(payload, null, 2)); // Log detailed payload for debugging
      this.dialogRef.close(payload);
    }
  }

  // Horarios FormArray helpers
  get horarios() {
    return this.puestoForm.get('horarios') as any;
  }

  addHorario(horas: number | null = 12, turno: string = 'Diurno', days: number[] = []) {
    const group = this.fb.group({
      horas: [horas ?? 12, Validators.required],
      turno: [turno, Validators.required],
      days: [days]
    });
    this.horarios.push(group);
  }

  removeHorario(index: number) {
    this.horarios.removeAt(index);
  }

  toggleDay(horarioIndex: number, day: number, checked: boolean) {
    const group = this.horarios.at(horarioIndex);
    const current: number[] = group.get('days').value || [];
    if (checked) {
      if (current.indexOf(day) === -1) current.push(day);
    } else {
      const idx = current.indexOf(day);
      if (idx !== -1) current.splice(idx, 1);
    }
    group.get('days').setValue(current);
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
