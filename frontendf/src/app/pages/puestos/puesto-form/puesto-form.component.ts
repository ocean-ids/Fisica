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
      horarios: this.fb.array([])
    });

    // initialize horarios from existing puesto or a single empty horario
    const initialHorarios = puesto?.horarios && Array.isArray(puesto.horarios) ? puesto.horarios : [];
    if (initialHorarios.length) {
      for (const h of initialHorarios) {
        this.addHorario(this.toTimeString(h.horas ?? 12), h.turno || 'Diurno', h.dia ? [h.dia] : []);
      }
    } else {
      this.addHorario('12:00', 'Diurno', []);
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
            horariosPayload.push({ dia: d, horas: this.toNumberHours(h.horas, h.turno), turno: h.turno });
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

  get horarios() {
    return this.puestoForm.get('horarios') as any;
  }

  addHorario(horas: string | number | null = '12:00', turno: string = 'Diurno', days: number[] = []) {
    const group = this.fb.group({
      horas: [horas ?? '12:00', Validators.required],
      turno: [turno, Validators.required],
      days: [days]
    });

    // Ajustar horas máximas según turno: Diurno/Nocturno hasta 12, Ambos hasta 24.
    group.get('turno')?.valueChanges.subscribe((t: string | null) => {
      const turnoVal = t ?? undefined;
      // Si es Ambos, sugerimos el máximo visible en input time (23:59) y lo tratamos como 24 al enviar
      if (turnoVal === 'Ambos') {
        group.get('horas')?.setValue('23:59', { emitEvent: false });
      }
      this.enforceHourLimit(group, turnoVal);
    });
    group.get('horas')?.valueChanges.subscribe(() => {
      this.enforceHourLimit(group, group.get('turno')?.value);
    });

    this.horarios.push(group);
  }

  private enforceHourLimit(group: any, turno?: string | null) {
    const horasCtrl = group.get('horas');
    if (!horasCtrl) return;
    const raw = horasCtrl.value;
    const val = this.toNumberHours(raw, turno);
    const max = (turno === 'Ambos') ? 24 : 12;
    const clamped = Math.min(Math.max(val, 0), max);
    if (clamped !== val) {
      // Para mostrar en input time, 24 se representa como 23:59
      horasCtrl.setValue(this.toTimeString(clamped === 24 ? 23.9833 : clamped), { emitEvent: false });
    }
  }

  private toNumberHours(raw: any, turno?: string | null): number {
    if (typeof raw === 'number') return raw;
    if (typeof raw === 'string' && raw.includes(':')) {
      const [hh, mm] = raw.split(':').map(Number);
      let total = (hh || 0) + (mm || 0) / 60;
      if (total > 23.9833 && (turno === 'Ambos' || turno === 'ambos')) {
        total = 24; // tratar 23:59 como 24h al enviar
      }
      const max = turno === 'Ambos' ? 24 : 12;
      return Math.min(Math.max(total, 0), max);
    }
    const n = Number(raw) || 0;
    const max = turno === 'Ambos' ? 24 : 12;
    return Math.min(Math.max(n, 0), max);
  }

  private toTimeString(hours: number | string): string {
    if (typeof hours === 'string') {
      if (hours.includes(':')) return hours;
      const n = Number(hours) || 0;
      const h = Math.floor(n);
      const m = Math.round((n - h) * 60);
      return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
    }
    // Si es 24, devolvemos 23:59 porque input time no admite 24:00
    if (hours >= 24) return '23:59';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
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
