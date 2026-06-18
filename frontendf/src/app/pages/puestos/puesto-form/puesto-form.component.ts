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
import { HorarioService } from '../../../services/horario.service';
import { Instalacion, Horario } from '../../../models';

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
  horariosCatalogo: Horario[] = [];
  private readonly TURNO_24H_UI = '24';
  private readonly TURNO_24H_BACKEND = 'Ambos';
  private readonly MAX_HORAS_TURNO = 24

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PuestoFormComponent>,
    private instalacionService: InstalacionService,
    private horarioService: HorarioService,
    @Inject(MAT_DIALOG_DATA) public data: { puesto: any, clienteId: number }
  ) {}

  ngOnInit(): void {
    const puesto = this.data.puesto || {};
    this.puestoForm = this.fb.group({
      nombre: [puesto?.nombre || '', Validators.required],
      tipo: [puesto?.tipo || ''],
      instalacion_id: [puesto?.instalacion_id || '', Validators.required],
      cantidad_puestos: [puesto?.cantidad_puestos ?? 0, Validators.required],
      horario: [puesto?.horario ?? null],
      horarios: this.fb.array([])
    });

    this.horarioService.obtenerHorarios().subscribe({
      next: data => this.horariosCatalogo = data || [],
      error: err => console.error('Error al cargar horarios', err)
    });

    
    const initialHorarios = puesto?.horarios && Array.isArray(puesto.horarios) ? puesto.horarios : [];
    if (initialHorarios.length) {
      
      const grouped: Record<string, { ingreso: string; salida: string; turno: string; days: number[]; horas: any }> = {};
      for (const h of initialHorarios) {
        const turno = this.toUiTurno(h.turno || 'Diurno');
        const ingreso = ((h as any).hora_ingreso || '07:00').toString().slice(0, 5);
        const salida = ((h as any).hora_salida || '19:00').toString().slice(0, 5);
        const key = `${ingreso}-${salida}-${turno}`;
        if (!grouped[key]) {
          grouped[key] = { ingreso, salida, turno, days: [], horas: (h as any).horas };
        }
        if (h.dia) {
          grouped[key].days.push(h.dia);
        }
      }
      Object.values(grouped).forEach(g => this.addHorario(g.ingreso, g.salida, g.turno, g.days, g.horas));
    } else {
      this.addHorario('07:00', '19:00', 'Diurno', []);
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

    if (v.includes('noct')) return 'Nocturno';
    if (v.includes('diurn')) return 'Diurno';
    return null;
  }

  onSubmit(): void {
    if (this.puestoForm.valid) {
      const formValue = this.puestoForm.value;
      const selectedInstalacion = this.instalaciones.find(i => i.id === formValue.instalacion_id);

      const horariosPayload: any[] = [];
      const horariosFA = this.puestoForm.get('horarios') as any;
      for (let i = 0; i < horariosFA.length; i++) {
        const h = horariosFA.at(i).getRawValue();
        const days: number[] = h.days || [];
        // El campo Horas viene en HH:MM (editable). Se convierte a decimal para guardar/resumen.
        const horasManual = this.hhmmToDecimal(h.horas);
        const horasDur = horasManual > 0 ? horasManual : this.calcDuracion(h.ingreso, h.salida);
        if (days.length) {
          for (const d of days) {
            horariosPayload.push({
              dia: d,
              horas: horasDur,
              turno: this.toBackendTurno(h.turno),
              hora_ingreso: h.ingreso,
              hora_salida: h.salida
            });
          }
        }
      }

      const payload: any = {
        ...formValue,
        horarios: horariosPayload,
        instalacion_nombre: selectedInstalacion?.nombre || null
      };
      console.log('Payload enviado:', JSON.stringify(payload, null, 2)); 
      this.dialogRef.close(payload);
    }
  }

  get horarios() {
    return this.puestoForm.get('horarios') as any;
  }

  addHorario(ingreso: string = '07:00', salida: string = '19:00', turno: string = 'Diurno', days: number[] = [], horasGuardadas?: number | string | null) {
    // Si viene un valor guardado (al editar), úsalo; si no, calcula desde Ingreso→Salida.
    const horasStr = (horasGuardadas !== undefined && horasGuardadas !== null && horasGuardadas !== '')
      ? this.decimalToHHMM(Number(horasGuardadas))
      : this.decimalToHHMM(this.calcDuracion(ingreso, salida));
    const group = this.fb.group({
      ingreso: [ingreso, Validators.required],
      salida: [salida, Validators.required],
      horas: [horasStr],  // duración en HH:MM (editable)
      turno: [turno, Validators.required],
      days: [days]
    });

    const recalcular = () => {
      const dur = this.calcDuracion(group.get('ingreso')?.value, group.get('salida')?.value);
      group.get('horas')?.setValue(this.decimalToHHMM(dur), { emitEvent: false });
    };
    group.get('ingreso')?.valueChanges.subscribe(recalcular);
    group.get('salida')?.valueChanges.subscribe(recalcular);

    // Al elegir Turno = 24, cargar 24:00 en Horas.
    group.get('turno')?.valueChanges.subscribe((t: string | null) => {
      if (this.is24hTurn(t)) {
        group.get('horas')?.setValue('24:00', { emitEvent: false });
      }
    });

    this.horarios.push(group);
  }

  // Decimal de horas -> "HH:MM" (13.5 -> "13:30").
  private decimalToHHMM(dec: number): string {
    const n = Number(dec) || 0;
    const h = Math.floor(n);
    const m = Math.round((n - h) * 60);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  // "HH:MM" -> decimal de horas (13:30 -> 13.5). Si ya es número, lo devuelve.
  private hhmmToDecimal(value: any): number {
    if (value === null || value === undefined || value === '') return 0;
    const s = value.toString();
    if (s.includes(':')) {
      const [hh, mm] = s.split(':').map(Number);
      return Math.round(((hh || 0) + (mm || 0) / 60) * 100) / 100;
    }
    return Math.round((Number(s) || 0) * 100) / 100;
  }

  // Duración en horas (decimal) entre ingreso y salida; contempla turnos que cruzan medianoche.
  private calcDuracion(ingreso?: string | null, salida?: string | null): number {
    if (!ingreso || !salida) return 0;
    const [hi, mi] = ingreso.split(':').map(Number);
    const [hs, ms] = salida.split(':').map(Number);
    let mins = (hs * 60 + ms) - (hi * 60 + mi);
    if (mins <= 0) mins += 24 * 60;             // ej. 19:00 -> 07:00 = 12h
    return Math.round((mins / 60) * 100) / 100; // 2 decimales (ej. 13.5)
  }

  private enforceHourLimit(group: any, turno?: string | null) {
    const horasCtrl = group.get('horas');
    if (!horasCtrl) return;
    const raw = horasCtrl.value;
    const val = this.toNumberHours(raw, turno);
    const max = this.is24hTurn(turno) ? 24 : this.MAX_HORAS_TURNO;
    const clamped = Math.min(Math.max(val, 0), max);
    if (clamped !== val) {
      
      horasCtrl.setValue(this.toTimeString(clamped === 24 ? 23.9833 : clamped), { emitEvent: false });
    }
  }

  private toNumberHours(raw: any, turno?: string | null): number {
    if (typeof raw === 'number') return raw;
    if (typeof raw === 'string' && raw.includes(':')) {
      const [hh, mm] = raw.split(':').map(Number);
      let total = (hh || 0) + (mm || 0) / 60;
      if (total > 23.9833 && this.is24hTurn(turno)) {
        total = 24; 
      }
      const max = this.is24hTurn(turno) ? 24 : this.MAX_HORAS_TURNO;
      return Math.min(Math.max(total, 0), max);
    }
    const n = Number(raw) || 0;
    const max = this.is24hTurn(turno) ? 24 : this.MAX_HORAS_TURNO;
    return Math.min(Math.max(n, 0), max);
  }

  private is24hTurn(turno?: string | null): boolean {
    const t = String(turno || '').trim().toLowerCase();
    return t === '24' || t === '24h' || t === 'ambos';
  }

  private toUiTurno(turno?: string | null): string {
    return this.is24hTurn(turno) ? this.TURNO_24H_UI : String(turno || 'Diurno');
  }

  private toBackendTurno(turno?: string | null): string {
    return this.is24hTurn(turno) ? this.TURNO_24H_BACKEND : String(turno || 'Diurno');
  }

  private toTimeString(hours: number | string): string {
    if (typeof hours === 'string') {
      if (hours.includes(':')) return hours;
      const n = Number(hours) || 0;
      const h = Math.floor(n);
      const m = Math.round((n - h) * 60);
      return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
    }
    
    if (hours >= 24) return '23:59';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
  }

  removeHorario(index: number) {
    this.horarios.removeAt(index);
  }

  toggleDay(horarioIndex: number, day: number, ev: Event) {
    const input = ev.target as HTMLInputElement;
    const checked = !!input?.checked;
    const group = this.horarios.at(horarioIndex);
    const current: number[] = group.get('days').value || [];

    if (checked) {
      // Se pueden marcar todos los días (sin límite). El resumen muestra el rango
      // primero–último (ej. todos = L–D).
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
