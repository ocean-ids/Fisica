import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { NovedadPuesto } from '../../../models/novedad-puesto.model';
import { PuestoService } from '../../../services/puesto.service';

interface DialogData {
  puestos?: any[];
  clienteNombre?: string;
  fecha?: string;
}

interface HorarioRow {
  ingreso: string;
  salida: string;
  horas: string;   // duración HH:MM (editable)
  turno: string;   // 'Diurno' | 'Nocturno' | '24'
  days: number[];  // 1=L ... 7=D
}

@Component({
  selector: 'app-novedad-puesto-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatDialogModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatButtonModule
  ],
  templateUrl: './novedad-puesto-dialog.component.html',
  styleUrl: './novedad-puesto-dialog.component.css'
})
export class NovedadPuestoDialogComponent implements OnInit {
  puestos: any[] = [];
  puestoId: number | null = null;

  model: NovedadPuesto = {
    fecha: '',
    turno: 'Diurno',
    cliente_denominativo: '',
    sector: '',
    novedad: 'MODIFICACION',
    tipo: '',
    horario: '',
    solicitado_por: '',
    observacion: '',
    puesto: null,
    instalacion: null,
  };

  novedades = [
    { value: 'APERTURA', label: 'Apertura' },
    { value: 'MODIFICACION', label: 'Modificación' },
    { value: 'CIERRE', label: 'Cierre' },
    { value: 'INCREMENTO', label: 'Incremento' },
    { value: 'MODIFICACION INCREMENTO', label: 'Modificación / Incremento' },
  ];

  // Editor de horario para Modificación (mismo concepto que "Editar Puesto").
  horariosEdit: HorarioRow[] = [];
  guardando = false;
  dias = [
    { n: 1, l: 'L' }, { n: 2, l: 'M' }, { n: 3, l: 'X' }, { n: 4, l: 'J' },
    { n: 5, l: 'V' }, { n: 6, l: 'S' }, { n: 7, l: 'D' },
  ];
  turnosEditor = [
    { v: 'Diurno', l: 'Diurno' }, { v: 'Nocturno', l: 'Nocturno' }, { v: '24', l: '24' },
  ];
  private readonly TURNO_24H_UI = '24';
  private readonly TURNO_24H_BACKEND = 'Ambos';

  constructor(
    private dialogRef: MatDialogRef<NovedadPuestoDialogComponent, NovedadPuesto | null>,
    private puestoService: PuestoService,
    @Inject(MAT_DIALOG_DATA) public data: DialogData | null
  ) {}

  ngOnInit(): void {
    this.puestos = this.data?.puestos || [];
    this.model.fecha = this.data?.fecha || this.hoyISO();
    if (this.data?.clienteNombre) {
      this.model.cliente_denominativo = this.data.clienteNombre;
    }
  }

  private hoyISO(): string {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;
  }

  // APERTURA -> solo puestos CERRADOS (reabrir). Resto (cierre, etc.) -> solo ACTIVOS.
  get puestosFiltrados(): any[] {
    const esApertura = (this.model.novedad || '').toString().toUpperCase() === 'APERTURA';
    return (this.puestos || []).filter(p =>
      esApertura ? p.activo === false : p.activo !== false
    );
  }

  onNovedadChange(): void {
    // Si el puesto elegido ya no aplica al tipo de novedad, limpiarlo.
    if (this.puestoId != null && !this.puestosFiltrados.some(p => p.id === this.puestoId)) {
      this.puestoId = null;
      this.onPuestoChange();
    }
    // Al pasar a Modificación con un puesto ya elegido, cargar su horario.
    if (this.esModificacion && this.puestoId != null && !this.horariosEdit.length) {
      const p = this.puestos.find(x => x.id === this.puestoId);
      if (p) this.cargarHorariosDe(p);
    }
  }

  get esModificacion(): boolean {
    const n = (this.model.novedad || '').toString().toUpperCase();
    return n === 'MODIFICACION' || n === 'MODIFICACION INCREMENTO';
  }

  get mostrarEditorHorario(): boolean {
    return this.esModificacion && this.puestoId != null && this.horariosEdit.length > 0;
  }

  onPuestoChange(): void {
    const p = this.puestos.find(x => x.id === this.puestoId);
    if (!p) {
      this.model.puesto = null;
      this.model.instalacion = null;
      return;
    }
    this.model.puesto = p.id;
    this.model.instalacion = p.instalacion_id ?? null;

    const denom = (p.instalacion_codigo || p.instalacion_nombre || '').toString().trim();
    const cliente = (this.data?.clienteNombre || '').trim();
    this.model.cliente_denominativo = denom
      ? (cliente ? `${cliente} - ${denom}` : denom)
      : cliente;

    this.model.sector = (p.instalacion_sector || '').toString();
    // Tipo = resumen de horario (fallback al resumen local mientras llega el endpoint)
    this.model.tipo = (p.resumen || '').toString();
    // Horario = secuencia de rotación D/N/F del calendario (ej. "331"). NO se borra aquí:
    // si la detección viene vacía, se conserva lo que el usuario ya tenga escrito.

    const turno = (p.turno || '').toString().toLowerCase();
    if (turno.startsWith('n')) this.model.turno = 'Nocturno';
    else if (turno.startsWith('d')) this.model.turno = 'Diurno';

    // Trae el resumen desde el backend para el "Tipo".
    // El "Horario" NO se autocompleta (antes salía "1"): se deja vacío y, si se
    // necesita, el usuario lo escribe manualmente.
    this.puestoService.getSecuenciaHorario(p.id).subscribe({
      next: (res) => {
        if (res?.resumen) this.model.tipo = res.resumen;
      },
      error: () => {}
    });

    // En Modificación, cargar el horario del puesto para poder editarlo.
    if (this.esModificacion) {
      this.cargarHorariosDe(p);
    } else {
      this.horariosEdit = [];
    }
  }

  // ---- Editor de horario (Modificación) ----
  private cargarHorariosDe(p: any): void {
    const arr = Array.isArray(p?.horarios) ? p.horarios : [];
    const grouped: Record<string, HorarioRow> = {};
    for (const h of arr) {
      const turno = this.toUiTurno(h.turno || 'Diurno');
      const ingreso = (h.hora_ingreso || '07:00').toString().slice(0, 5);
      const salida = (h.hora_salida || '19:00').toString().slice(0, 5);
      const key = `${ingreso}-${salida}-${turno}`;
      if (!grouped[key]) {
        const horas = (h.horas !== undefined && h.horas !== null && h.horas !== '')
          ? this.decimalToHHMM(Number(h.horas))
          : this.decimalToHHMM(this.calcDuracion(ingreso, salida));
        grouped[key] = { ingreso, salida, horas, turno, days: [] };
      }
      if (h.dia) grouped[key].days.push(h.dia);
    }
    this.horariosEdit = Object.values(grouped);
    if (!this.horariosEdit.length) {
      this.horariosEdit = [{ ingreso: '07:00', salida: '19:00', horas: '12:00', turno: 'Diurno', days: [] }];
    }
    this.recomputeTipo();
  }

  addHorario(): void {
    this.horariosEdit.push({ ingreso: '07:00', salida: '19:00', horas: '12:00', turno: 'Diurno', days: [] });
    this.recomputeTipo();
  }

  removeHorario(i: number): void {
    this.horariosEdit.splice(i, 1);
    this.recomputeTipo();
  }

  toggleDay(row: HorarioRow, day: number, ev: Event): void {
    const checked = !!(ev.target as HTMLInputElement)?.checked;
    const idx = row.days.indexOf(day);
    if (checked && idx === -1) row.days.push(day);
    else if (!checked && idx !== -1) row.days.splice(idx, 1);
    this.recomputeTipo();
  }

  onIngresoSalida(row: HorarioRow): void {
    if (!this.is24hTurn(row.turno)) {
      row.horas = this.decimalToHHMM(this.calcDuracion(row.ingreso, row.salida));
    }
    this.recomputeTipo();
  }

  onTurnoEditorChange(row: HorarioRow): void {
    if (this.is24hTurn(row.turno)) {
      row.horas = '24:00';
    } else {
      row.horas = this.decimalToHHMM(this.calcDuracion(row.ingreso, row.salida));
    }
    this.recomputeTipo();
  }

  recomputeTipo(): void {
    const r = this.buildResumen();
    if (r) this.model.tipo = r;
  }

  // Resumen estilo backend: "1 {horas}H{D|N|''}{dias}" (ej. "1 24HDLD").
  private buildResumen(): string {
    const rows = this.horariosEdit.filter(r => (r.days || []).length);
    if (!rows.length) return '';
    const horasSet = new Set<number>();
    const turnosSet = new Set<string>();
    const allDays: number[] = [];
    for (const r of rows) {
      horasSet.add(this.hhmmToDecimal(r.horas));
      turnosSet.add(this.toBackendTurno(r.turno).toLowerCase());
      for (const d of r.days) allDays.push(d);
    }
    const horas = horasSet.size === 1 ? [...horasSet][0] : 0;
    let turnoLetter = 'M';
    if (turnosSet.size === 1) {
      const v = [...turnosSet][0];
      if (v.startsWith('d')) turnoLetter = 'D';
      else if (v.startsWith('n')) turnoLetter = 'N';
      else turnoLetter = '';
    }
    return `1 ${this.fmtHoras(horas)}H${turnoLetter}${this.formatDiasRange(allDays)}`;
  }

  private formatDiasRange(daysNums: number[]): string {
    if (!daysNums.length) return '';
    const map: Record<number, string> = { 1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D' };
    const ordered = [...new Set(daysNums)].sort((a, b) => a - b);
    if (ordered.length === 1) return map[ordered[0]] || '';
    const first = map[ordered[0]] || '';
    const last = map[ordered[ordered.length - 1]] || '';
    return (first || last) ? `${first}${last}` : '';
  }

  private fmtHoras(h: number): string {
    const n = Number(h) || 0;
    return n.toString();
  }

  private decimalToHHMM(dec: number): string {
    const n = Number(dec) || 0;
    const h = Math.floor(n);
    const m = Math.round((n - h) * 60);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  private hhmmToDecimal(value: any): number {
    if (value === null || value === undefined || value === '') return 0;
    const s = value.toString();
    if (s.includes(':')) {
      const [hh, mm] = s.split(':').map(Number);
      return Math.round(((hh || 0) + (mm || 0) / 60) * 100) / 100;
    }
    return Math.round((Number(s) || 0) * 100) / 100;
  }

  private calcDuracion(ingreso?: string | null, salida?: string | null): number {
    if (!ingreso || !salida) return 0;
    const [hi, mi] = ingreso.split(':').map(Number);
    const [hs, ms] = salida.split(':').map(Number);
    let mins = (hs * 60 + ms) - (hi * 60 + mi);
    if (mins <= 0) mins += 24 * 60;
    return Math.round((mins / 60) * 100) / 100;
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

  isValid(): boolean {
    return !!this.model.fecha && !!this.model.novedad && !!this.model.cliente_denominativo.trim();
  }

  guardar(): void {
    if (!this.isValid() || this.guardando) return;

    // Modificación: aplicar los cambios de horario al puesto antes de registrar la novedad.
    if (this.esModificacion && this.puestoId != null && this.horariosEdit.length) {
      const horarios: any[] = [];
      for (const r of this.horariosEdit) {
        const horasDec = this.hhmmToDecimal(r.horas) || this.calcDuracion(r.ingreso, r.salida);
        for (const d of (r.days || [])) {
          horarios.push({
            dia: d,
            horas: horasDec,
            turno: this.toBackendTurno(r.turno),
            hora_ingreso: r.ingreso,
            hora_salida: r.salida,
          });
        }
      }
      if (!horarios.length) {
        // Sin días marcados: no se toca el horario, solo se registra la novedad.
        this.dialogRef.close({ ...this.model });
        return;
      }
      this.guardando = true;
      const pid = this.puestoId;
      this.puestoService.actualizarPuesto(pid, { horarios } as any).subscribe({
        next: () => {
          // Refrescar el resumen real para el "Tipo" de la novedad.
          this.puestoService.getSecuenciaHorario(pid).subscribe({
            next: (res) => {
              if (res?.resumen) this.model.tipo = res.resumen;
              this.guardando = false;
              this.dialogRef.close({ ...this.model });
            },
            error: () => { this.guardando = false; this.dialogRef.close({ ...this.model }); }
          });
        },
        error: () => { this.guardando = false; this.dialogRef.close({ ...this.model }); }
      });
      return;
    }

    this.dialogRef.close({ ...this.model });
  }

  cancelar(): void {
    this.dialogRef.close(null);
  }
}
