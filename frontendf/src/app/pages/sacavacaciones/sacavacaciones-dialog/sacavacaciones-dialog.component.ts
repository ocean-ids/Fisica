import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl, FormGroup } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { Observable } from 'rxjs';
import { debounceTime, startWith, map } from 'rxjs/operators';
import { PersonaService } from '../../../services/persona.service';
import { ReporteVacacionesService } from '../../../services/reporte-vacaciones.service';
import { Persona } from '../../../models/persona.model';
import { ReporteVacaciones } from '../../../models/reporte-vacaciones.model';

interface DialogData {
  row?: ReporteVacaciones;   // presente = edición
  anioDefecto?: number | null;   // al crear: año en que se abre el calendario
}

@Component({
  selector: 'app-sacavacaciones-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule,
    MatFormFieldModule, MatInputModule, MatSelectModule, MatAutocompleteModule, MatButtonModule,
    MatDatepickerModule,
  ],
  templateUrl: './sacavacaciones-dialog.component.html',
  styleUrl: './sacavacaciones-dialog.component.css',
})
export class SacavacacionesDialogComponent implements OnInit {
  personasAll: Persona[] = [];

  // Autocargado desde la asignacion de la persona que sale de vacaciones.
  asignacionId: number | null = null;
  clienteNombre = '';
  instalacionNombre = '';
  puestoNombre = '';
  cargandoAsig = false;
  asigError = '';

  // Persona que sale de vacaciones
  saleCtrl = new FormControl<any>('');
  saleFiltradas$!: Observable<Persona[]>;
  saleSel: Persona | null = null;

  // Persona que cubre (sacavacaciones)
  cubreCtrl = new FormControl<any>('');
  cubreFiltradas$!: Observable<Persona[]>;
  cubreSel: Persona | null = null;

  periodo = '';
  periodoManual = '';                 // cuando se elige "Otro"
  periodos: string[] = [];            // opciones del desplegable
  readonly OTRO = 'OTRO';
  // Vacaciones (rango): al marcar Desde sugiere 15 días; el usuario hace clic en
  // el Hasta para fijar el día (puede ser el 15 o más).
  fechaDesde: Date | null = null;
  fechaHasta: Date | null = null;
  rangoForm = new FormGroup({
    start: new FormControl<Date | null>(null),
    end: new FormControl<Date | null>(null),
  });
  dias: number | null = null;

  // Días pendientes: otro rango (mismo picker) por si no le dieron todas.
  fechaDesdePend: Date | null = null;
  fechaHastaPend: Date | null = null;
  rangoPendForm = new FormGroup({
    start: new FormControl<Date | null>(null),
    end: new FormControl<Date | null>(null),
  });
  diasPend: number | null = null;
  esEdicion = false;
  // Año al que pertenece el registro (lo usa el filtro). Editable.
  anio: number | null = null;
  private editSaleId: number | null = null;
  private editCubreId: number | null = null;

  constructor(
    private ref: MatDialogRef<SacavacacionesDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private personaSrv: PersonaService,
    private vacSrv: ReporteVacacionesService,
  ) {}

  ngOnInit(): void {
    // Períodos alrededor del año actual: bastantes años hacia atrás (para las
    // vacaciones pendientes de años pasados) y un par hacia adelante.
    const y = new Date().getFullYear();
    this.periodos = [];
    for (let i = -12; i <= 10; i++) { this.periodos.push(`${y + i} - ${y + i + 1}`); }

    const row = this.data?.row;
    this.esEdicion = !!row?.id;
    // Año del registro: al editar sale del registro (respaldo: año de fecha_desde);
    // al crear sale del filtro activo (o el año actual).
    if (this.esEdicion) {
      this.anio = row?.anio ?? (row?.fecha_desde ? Number(String(row.fecha_desde).slice(0, 4)) : null);
    } else {
      this.anio = this.data?.anioDefecto || new Date().getFullYear();
    }
    if (row) {
      // Si el período guardado está en la lista, se selecciona; si no, es "Otro".
      const p = row.periodo || '';
      if (p && !this.periodos.includes(p)) {
        this.periodo = this.OTRO;
        this.periodoManual = p;
      } else {
        this.periodo = p;
      }
      this.fechaDesde = this._fromISO(row.fecha_desde);
      this.fechaHasta = this._fromISO(row.fecha_hasta);
      this.rangoForm.setValue({ start: this.fechaDesde, end: this.fechaHasta });
      this.dias = (row.dias ?? null) as number | null;
      this.fechaDesdePend = this._fromISO(row.fecha_desde_pendiente);
      this.fechaHastaPend = this._fromISO(row.fecha_hasta_pendiente);
      this.rangoPendForm.setValue({ start: this.fechaDesdePend, end: this.fechaHastaPend });
      this.diasPend = (row.dias_pendientes ?? null) as number | null;
      this.editSaleId = row.persona_sale_ref ?? null;
      this.editCubreId = row.sacavacaciones_ref ?? null;
      if (row.persona_sale) { this.saleCtrl.setValue(row.persona_sale); }
      if (row.sacavacaciones) { this.cubreCtrl.setValue(row.sacavacaciones); }
      // Datos del puesto ya guardados (autocargados al crear).
      this.asignacionId = row.asignacion ?? null;
      this.clienteNombre = row.cliente || '';
      this.instalacionNombre = row.instalacion || '';
      this.puestoNombre = row.puesto || '';
    }

    // Vacaciones: el rango se fija con dos clics (inicio + fin que elige el usuario).
    this.rangoForm.valueChanges.subscribe((v) => {
      this.fechaDesde = v.start ?? null;
      this.fechaHasta = v.end ?? null;
      this.calcularDias();
      this.recalcularPendientes();   // el total cambió: recalcular pendientes
    });
    // Rango de días DADOS (lo que sí se le dio): días pendientes = total − dados.
    this.rangoPendForm.valueChanges.subscribe((v) => {
      this.fechaDesdePend = v.start ?? null;
      this.fechaHastaPend = v.end ?? null;
      this.recalcularPendientes();
    });

    this.personaSrv.getPersonas({}).subscribe((ps) => { this.personasAll = ps || []; });
    this.saleFiltradas$ = this.filtro(this.saleCtrl);
    // "Quién cubre": salen TODOS, pero los SACAVACACIONES primero.
    this.cubreFiltradas$ = this.filtro(this.cubreCtrl, 'SACAVACACIONES');
  }

  private filtro(ctrl: FormControl, prioriTipo?: string): Observable<Persona[]> {
    return ctrl.valueChanges.pipe(
      startWith(''),
      debounceTime(120),
      map((val: any) => {
        const q = (typeof val === 'string' ? val : this.displayPersona(val)).toLowerCase().trim();
        const tokens = q.split(/\s+/).filter(Boolean);
        // Todas las personas (o las que coinciden con la búsqueda; cada palabra en cualquier orden).
        let base = tokens.length
          ? this.personasAll.filter(p => {
              const hay = `${p.nombres || ''} ${p.apellidos || ''} ${p.cedula || ''}`.toLowerCase();
              return tokens.every(t => hay.includes(t));
            })
          : this.personasAll;
        // Si hay un tipo prioritario, ese tipo va PRIMERO (pero salen TODOS).
        if (prioriTipo) {
          base = [...base].sort((a, b) => {
            const pa = String(a.tipo || '').toUpperCase() === prioriTipo ? 0 : 1;
            const pb = String(b.tipo || '').toUpperCase() === prioriTipo ? 0 : 1;
            return pa - pb;
          });
        }
        return base.slice(0, 200);
      }),
    );
  }

  displayPersona = (p: any): string => {
    if (!p) { return ''; }
    if (typeof p === 'string') { return p; }
    return `${p.nombres || ''} ${p.apellidos || ''}`.trim();
  };

  onSaleSel(p: Persona): void {
    this.saleSel = p;
    // Autocargar cliente / instalacion / puesto desde la asignacion activa de la persona.
    this.asignacionId = null;
    this.clienteNombre = '';
    this.instalacionNombre = '';
    this.puestoNombre = '';
    this.asigError = '';
    if (!p?.id) { return; }
    this.cargandoAsig = true;
    this.vacSrv.asignacionDePersona(p.id).subscribe({
      next: (r) => {
        this.asignacionId = r.asignacion_id;
        this.clienteNombre = r.cliente || '';
        this.instalacionNombre = r.instalacion || '';
        this.puestoNombre = r.puesto || '';
      },
      error: () => {
        this.asigError = 'Esta persona no tiene una asignación activa (no se puede cubrir un puesto).';
      },
      complete: () => { this.cargandoAsig = false; },
    });
  }
  onCubreSel(p: Persona): void { this.cubreSel = p; }

  // Los calendarios se abren: en edición, en la fecha ya guardada; al crear, en HOY
  // (para que el usuario elija fechas del período vigente, no de enero).
  get startAt(): Date {
    if (this.fechaDesde) { return this.fechaDesde; }
    const hoy = new Date();
    // Si el año del registro difiere del actual, abrir en ese año pero en el mes de hoy.
    if (this.anio && this.anio !== hoy.getFullYear()) {
      return new Date(this.anio, hoy.getMonth(), 1);
    }
    return hoy;
  }

  fmt(d: Date | null): string {
    if (!d) { return '—'; }
    const day = String(d.getDate()).padStart(2, '0');
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${day}/${m}/${d.getFullYear()}`;
  }

  // Días = contador de días calendario inclusive entre dos fechas.
  private _diasInclusive(d1: Date | null, d2: Date | null): number {
    if (!d1 || !d2) { return 0; }
    const diff = Math.round((d2.getTime() - d1.getTime()) / 86400000) + 1;
    return diff > 0 ? diff : 0;
  }

  calcularDias(): void {
    this.dias = this._diasInclusive(this.fechaDesde, this.fechaHasta);
  }

  // Días pendientes = total de vacaciones − días DADOS (el 2º rango).
  // Si no hay 2º rango, no hay pendientes (0).
  recalcularPendientes(): void {
    const dados = this._diasInclusive(this.fechaDesdePend, this.fechaHastaPend);
    this.diasPend = dados > 0 ? Math.max(0, (this.dias || 0) - dados) : 0;
  }

  // 'YYYY-MM-DD' (texto del backend) -> Date local. Y viceversa (sin corrimiento
  // de zona horaria).
  private _fromISO(s: any): Date | null {
    if (!s) { return null; }
    const [y, m, d] = String(s).slice(0, 10).split('-').map(Number);
    return (y && m && d) ? new Date(y, m - 1, d) : null;
  }
  private _toISO(d: Date | null): string | null {
    if (!d) { return null; }
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  get valido(): boolean {
    // Debe haberse autocargado la asignación (puesto) de la persona que sale.
    const tienePuesto = !!this.asignacionId || (this.esEdicion && !!this.clienteNombre);
    return tienePuesto && (!!this.saleSel || (this.esEdicion && !!this.saleCtrl.value));
  }

  guardar(): void {
    const out: any = {
      cliente: this.clienteNombre || '',
      asignacion: this.asignacionId,
      instalacion: this.instalacionNombre || '',
      puesto: this.puestoNombre || '',
      anio: this.anio || null,
      periodo: (this.periodo === this.OTRO ? this.periodoManual : this.periodo || '').trim(),
      fecha_desde: this._toISO(this.fechaDesde),
      fecha_hasta: this._toISO(this.fechaHasta),
      dias: this.dias || 0,
      fecha_desde_pendiente: this._toISO(this.fechaDesdePend),
      fecha_hasta_pendiente: this._toISO(this.fechaHastaPend),
      dias_pendientes: this.diasPend || 0,
    };
    // Persona que sale
    if (this.saleSel) {
      out.persona_sale = `${this.saleSel.nombres} ${this.saleSel.apellidos}`.trim();
      out.persona_sale_ref = this.saleSel.id;
    } else {
      out.persona_sale = typeof this.saleCtrl.value === 'string' ? this.saleCtrl.value : '';
      out.persona_sale_ref = this.editSaleId;
    }
    // Persona que cubre (opcional -> N/A)
    if (this.cubreSel) {
      out.sacavacaciones = `${this.cubreSel.nombres} ${this.cubreSel.apellidos}`.trim();
      out.sacavacaciones_ref = this.cubreSel.id;
    } else {
      const txt = typeof this.cubreCtrl.value === 'string' ? this.cubreCtrl.value.trim() : '';
      out.sacavacaciones = txt;
      out.sacavacaciones_ref = this.editCubreId;
    }
    this.ref.close(out);
  }

  cancelar(): void { this.ref.close(); }
}
