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
  // Tipos de puesto (lista fija, ya no texto libre).
  readonly tiposPuestoBase = ['GARITA', 'RONDA', 'FIJO', 'INGRESO', 'CONTROL DE ACCESO (PERSONAS/VEHICULOS)'];
  // Opciones a mostrar: las fijas + el tipo actual si es uno distinto (para no perderlo al editar).
  get tiposPuestoOpciones(): string[] {
    const actual = (this.puestoForm?.get('tipo')?.value || '').toString().trim();
    if (actual && !this.tiposPuestoBase.includes(actual)) {
      return [...this.tiposPuestoBase, actual];
    }
    return this.tiposPuestoBase;
  }
  // Reglas para sugerir el codigo del puesto (mismas del backend): el TIPO manda
  // y, si no define uno conocido, cae al NOMBRE. GARITA->G RONDA->R FIJO->F
  // INGRESO->I CONTROL DE ACCESO->C.
  private readonly tipoDefs: { letra: string; rx: RegExp }[] = [
    { letra: 'C', rx: /CONTROL\s+DE\s+ACCESO\s*0*(\d+)?/i },
    { letra: 'G', rx: /GARITA\s*0*(\d+)?/i },
    { letra: 'R', rx: /RONDA\s*0*(\d+)?/i },
    { letra: 'I', rx: /INGRESO\s*0*(\d+)?/i },
    { letra: 'F', rx: /FIJO\s*0*(\d+)?/i },
  ];

  // Codigo sugerido (G1/R1/F1/I1/C1) segun el Tipo elegido o el nombre.
  get codigoSugerido(): string {
    const tipo = (this.puestoForm?.get('tipo')?.value || '').toString();
    const nombre = (this.puestoForm?.get('nombre')?.value || '').toString();
    for (const fuente of [tipo, nombre]) {
      let best: { pos: number; letra: string; num: string } | null = null;
      for (const d of this.tipoDefs) {
        const m = d.rx.exec(fuente);
        if (m && (best === null || m.index < best.pos)) {
          best = { pos: m.index, letra: d.letra, num: m[1] || '1' };
        }
      }
      if (best) { return `${best.letra}${parseInt(best.num, 10)}`; }
    }
    return '';
  }

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
    const initialHorarios = puesto?.horarios && Array.isArray(puesto.horarios) ? puesto.horarios : [];

    this.puestoForm = this.fb.group({
      nombre: [puesto?.nombre || '', Validators.required],
      codigo: [puesto?.codigo || ''],
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

    if (initialHorarios.length) {
      // Un bloque por TURNO, con SU propia hora de ingreso/salida (dia y noche distintos).
      const grouped: Record<string, { turno: string; days: number[]; horas: any; ing: string; sal: string }> = {};
      for (const h of initialHorarios) {
        const turno = this.toUiTurno(h.turno || 'Diurno');
        if (!grouped[turno]) {
          grouped[turno] = {
            turno, days: [], horas: (h as any).horas,
            ing: ((h as any).hora_ingreso || '').toString().slice(0, 5),
            sal: ((h as any).hora_salida || '').toString().slice(0, 5),
          };
        }
        if (h.dia) { grouped[turno].days.push(h.dia); }
      }
      Object.values(grouped).forEach(g => this.addHorario(g.turno, g.days, g.horas, g.ing, g.sal));
    } else {
      this.addHorario('Diurno', []);
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

      // Cada bloque (turno) tiene SU propia hora de ingreso/salida (dia/noche distintos).
      const horariosPayload: any[] = [];
      const horariosFA = this.puestoForm.get('horarios') as any;
      for (let i = 0; i < horariosFA.length; i++) {
        const h = horariosFA.at(i).getRawValue();
        const days: number[] = h.days || [];
        const bIng = h.ingreso;
        const bSal = h.salida;
        // El campo Horas viene en HH:MM (editable). Se convierte a decimal para guardar/resumen.
        const horasManual = this.hhmmToDecimal(h.horas);
        const horasDur = horasManual > 0 ? horasManual : this.calcDuracion(bIng, bSal);
        if (days.length) {
          for (const d of days) {
            horariosPayload.push({
              dia: d,
              horas: horasDur,
              turno: this.toBackendTurno(h.turno),
              hora_ingreso: bIng,
              hora_salida: bSal
            });
          }
        }
      }

      const payload: any = {
        ...formValue,
        codigo: (formValue.codigo || '').toString().trim().toUpperCase() || null,
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

  // Hora de ingreso/salida por defecto segun el turno (editable). Diurno 07-19,
  // Nocturno 19-07, 24h 07-07.
  private defaultHoras(turno: string): { ing: string; sal: string } {
    const t = (turno || '').toLowerCase();
    if (t.startsWith('n')) return { ing: '19:00', sal: '07:00' };
    if (t === '24' || t.startsWith('a')) return { ing: '07:00', sal: '07:00' };
    return { ing: '07:00', sal: '19:00' };
  }

  addHorario(turno: string = 'Diurno', days: number[] = [], horasGuardadas?: number | string | null,
             ingreso?: string, salida?: string) {
    const def = this.defaultHoras(turno);
    const ing = (ingreso && ingreso.length >= 4) ? ingreso.slice(0, 5) : def.ing;
    const sal = (salida && salida.length >= 4) ? salida.slice(0, 5) : def.sal;
    const horasStr = (horasGuardadas !== undefined && horasGuardadas !== null && horasGuardadas !== '')
      ? this.decimalToHHMM(Number(horasGuardadas))
      : this.decimalToHHMM(this.calcDuracion(ing, sal));
    const group = this.fb.group({
      horas: [horasStr],  // duración en HH:MM (editable)
      turno: [turno, Validators.required],
      ingreso: [ing, Validators.required],
      salida: [sal, Validators.required],
      days: [days]
    });

    // Al cambiar el TURNO: reponer la hora default de ese turno y recalcular horas.
    group.get('turno')?.valueChanges.subscribe((t: string | null) => {
      const d = this.defaultHoras(t || 'Diurno');
      group.get('ingreso')?.setValue(d.ing, { emitEvent: false });
      group.get('salida')?.setValue(d.sal, { emitEvent: false });
      if (this.is24hTurn(t)) {
        group.get('horas')?.setValue('24:00', { emitEvent: false });
      } else {
        group.get('horas')?.setValue(this.decimalToHHMM(this.calcDuracion(d.ing, d.sal)), { emitEvent: false });
      }
    });

    // Al cambiar la hora del bloque: recalcular sus horas.
    const recomputa = () => {
      if (this.is24hTurn(group.get('turno')?.value)) return;
      const dur = this.calcDuracion(group.get('ingreso')?.value, group.get('salida')?.value);
      group.get('horas')?.setValue(this.decimalToHHMM(dur), { emitEvent: false });
    };
    group.get('ingreso')?.valueChanges.subscribe(recomputa);
    group.get('salida')?.valueChanges.subscribe(recomputa);

    this.horarios.push(group);
  }

  // Recalcula las horas de todos los bloques cuando cambia la hora del puesto (ingreso/salida).
  private recalcularTodos(): void {
    const dur = this.calcDuracion(this.puestoForm.get('ingreso')?.value, this.puestoForm.get('salida')?.value);
    const hhmm = this.decimalToHHMM(dur);
    for (let i = 0; i < this.horarios.length; i++) {
      const g = this.horarios.at(i);
      if (!this.is24hTurn(g.get('turno')?.value)) {
        g.get('horas')?.setValue(hhmm, { emitEvent: false });
      }
    }
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
    const current: number[] = [...(group.get('days')?.value || [])];

    if (checked) {
      if (current.indexOf(day) === -1) current.push(day);
      // Un día puede estar en DIURNO y NOCTURNO a la vez (turnos distintos), pero no
      // repetido en dos bloques del MISMO turno. Solo se quita de otros bloques del
      // mismo turno.
      const miTurno = group.get('turno')?.value;
      for (let i = 0; i < this.horarios.length; i++) {
        if (i === horarioIndex) { continue; }
        const otro = this.horarios.at(i);
        if (otro.get('turno')?.value !== miTurno) { continue; }
        const otrosDias: number[] = otro.get('days')?.value || [];
        if (otrosDias.indexOf(day) !== -1) {
          otro.get('days')?.setValue(otrosDias.filter(d => d !== day));
        }
      }
    } else {
      const idx = current.indexOf(day);
      if (idx !== -1) current.splice(idx, 1);
    }
    group.get('days')?.setValue(current);
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
