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
import { Observable, BehaviorSubject, combineLatest } from 'rxjs';
import { debounceTime, startWith, map } from 'rxjs/operators';
import { PersonaService } from '../../../services/persona.service';
import { ReporteVacacionesService } from '../../../services/reporte-vacaciones.service';
import { Persona } from '../../../models/persona.model';
import { ReporteVacaciones } from '../../../models/reporte-vacaciones.model';
import Swal from 'sweetalert2';

interface DialogData {
  row?: ReporteVacaciones;   // presente = edición
  anioDefecto?: number | null;
  existentes?: ReporteVacaciones[];   // otros registros BACKUP (para avisar duplicados)
}

/**
 * Módulo EVENTUALES (backup): un FIJO/SACAFRANCO sale y lo cubre un EVENTUAL durante un
 * rango ("Backup"). Solo se refleja en la reportería (no toca Asignaciones), igual que
 * sacavacaciones. Sin período ni días dados/pendientes.
 */
@Component({
  selector: 'app-eventuales-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule,
    MatFormFieldModule, MatInputModule, MatSelectModule, MatAutocompleteModule, MatButtonModule,
    MatDatepickerModule,
  ],
  templateUrl: './eventuales-dialog.component.html',
  styleUrl: './eventuales-dialog.component.css',
})
export class EventualesDialogComponent implements OnInit {
  personasAll: Persona[] = [];
  private personas$ = new BehaviorSubject<Persona[]>([]);
  private asignados$ = new BehaviorSubject<Set<number> | null>(null);

  asignacionId: number | null = null;
  clienteNombre = '';
  instalacionNombre = '';
  puestoNombre = '';
  cargandoAsig = false;
  asigError = '';

  // Fijo/Sacafranco que sale
  saleCtrl = new FormControl<any>('');
  saleFiltradas$!: Observable<Persona[]>;
  saleSel: Persona | null = null;

  // Eventual que cubre
  cubreCtrl = new FormControl<any>('');
  cubreFiltradas$!: Observable<Persona[]>;
  cubreSel: Persona | null = null;

  // Rango "Backup" (Desde – Hasta)
  fechaDesde: Date | null = null;
  fechaHasta: Date | null = null;
  rangoForm = new FormGroup({
    start: new FormControl<Date | null>(null),
    end: new FormControl<Date | null>(null),
  });
  dias: number | null = null;

  esEdicion = false;
  anio: number | null = null;
  private editSaleId: number | null = null;
  private editCubreId: number | null = null;
  private existentes: ReporteVacaciones[] = [];

  constructor(
    private ref: MatDialogRef<EventualesDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private personaSrv: PersonaService,
    private vacSrv: ReporteVacacionesService,
  ) {}

  ngOnInit(): void {
    this.existentes = this.data?.existentes || [];
    const row = this.data?.row;
    this.esEdicion = !!row?.id;
    if (this.esEdicion) {
      this.anio = row?.anio ?? (row?.fecha_desde ? Number(String(row.fecha_desde).slice(0, 4)) : null);
    } else {
      this.anio = this.data?.anioDefecto || new Date().getFullYear();
    }
    if (row) {
      this.fechaDesde = this._fromISO(row.fecha_desde);
      this.fechaHasta = this._fromISO(row.fecha_hasta);
      this.rangoForm.setValue({ start: this.fechaDesde, end: this.fechaHasta });
      this.dias = (row.dias ?? null) as number | null;
      this.editSaleId = row.persona_sale_ref ?? null;
      this.editCubreId = row.sacavacaciones_ref ?? null;
      if (row.persona_sale) { this.saleCtrl.setValue(row.persona_sale); }
      if (row.sacavacaciones) { this.cubreCtrl.setValue(row.sacavacaciones); }
      this.asignacionId = row.asignacion ?? null;
      this.clienteNombre = row.cliente || '';
      this.instalacionNombre = row.instalacion || '';
      this.puestoNombre = row.puesto || '';
    }

    this.rangoForm.valueChanges.subscribe((v) => {
      this.fechaDesde = v.start ?? null;
      this.fechaHasta = v.end ?? null;
      this.calcularDias();
      this.checkEventualOcupado();   // al fijar el rango, revisa si el eventual se solapa
    });

    this.personaSrv.getPersonas({}).subscribe((ps) => {
      this.personasAll = ps || [];
      this.personas$.next(this.personasAll);
    });

    const now = new Date();
    this.vacSrv.personasAsignadas(now.getMonth() + 1, now.getFullYear()).subscribe({
      next: (r) => this.asignados$.next(new Set((r?.persona_ids || []).map(Number))),
      error: () => this.asignados$.next(null),
    });

    // "Fijos": fijos con asignación activa + sacafranco (que no tienen asignación fija).
    const salesSource$ = combineLatest([this.personas$, this.asignados$]).pipe(
      map(([ps, set]) => (set == null ? ps : ps.filter(p =>
        set.has(Number(p.id)) || String(p.tipo || '').toUpperCase() === 'SACAFRANCO'
      ))),
    );
    this.saleFiltradas$ = this.filtro(this.saleCtrl, salesSource$);

    // "Eventual": SOLO personas tipo EVENTUAL.
    const eventualesSource$ = this.personas$.pipe(
      map(ps => ps.filter(p => String(p.tipo || '').toUpperCase() === 'EVENTUAL')),
    );
    this.cubreFiltradas$ = this.filtro(this.cubreCtrl, eventualesSource$);
  }

  private filtro(ctrl: FormControl, source$: Observable<Persona[]>): Observable<Persona[]> {
    return combineLatest([
      source$,
      ctrl.valueChanges.pipe(startWith(ctrl.value ?? '')),
    ]).pipe(
      debounceTime(80),
      map(([personas, val]: [Persona[], any]) => {
        const q = (typeof val === 'string' ? val : this.displayPersona(val)).toLowerCase().trim();
        const tokens = q.split(/\s+/).filter(Boolean);
        const base = tokens.length
          ? personas.filter(p => {
              const hay = `${p.nombres || ''} ${p.apellidos || ''} ${p.cedula || ''}`.toLowerCase();
              return tokens.every(t => hay.includes(t));
            })
          : personas;
        return base.slice(0, 200);
      }),
    );
  }

  displayPersona = (p: any): string => {
    if (!p) { return ''; }
    if (typeof p === 'string') { return p; }
    return `${p.apellidos || ''} ${p.nombres || ''}`.trim();
  };

  limpiarSale(ev?: Event): void {
    ev?.stopPropagation();
    this.saleCtrl.setValue('');
    this.saleSel = null;
    this.editSaleId = null;
    this.asignacionId = null;
    this.clienteNombre = '';
    this.instalacionNombre = '';
    this.puestoNombre = '';
    this.asigError = '';
  }

  limpiarCubre(ev?: Event): void {
    ev?.stopPropagation();
    this.cubreCtrl.setValue('');
    this.cubreSel = null;
    this.editCubreId = null;
  }

  onSaleSel(p: Persona): void {
    this.saleSel = p;
    this.asignacionId = null;
    this.clienteNombre = '';
    this.instalacionNombre = '';
    this.puestoNombre = '';
    this.asigError = '';
    if (!p?.id) { return; }
    // Sacafranco: no tiene puesto fijo. Cliente = OCEANSECURITY; instalación/puesto vacíos.
    if (String(p.tipo || '').toUpperCase() === 'SACAFRANCO') {
      this.clienteNombre = 'OCEANSECURITY';
      this.instalacionNombre = '';
      this.puestoNombre = '';
      return;
    }
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
  onCubreSel(p: Persona): void {
    this.cubreSel = p;
    this.checkEventualOcupado();
  }

  // Avisa (SweetAlert2) si el eventual elegido ya está cubriendo otro puesto en fechas
  // que se solapan con el rango actual (evita doble asignación del mismo eventual).
  private checkEventualOcupado(): void {
    const evId = this.cubreSel?.id ?? this.editCubreId;
    if (!evId || !this.fechaDesde || !this.fechaHasta) { return; }
    const conflicto = this.existentes.find(f =>
      f.id !== this.data?.row?.id &&
      f.sacavacaciones_ref === evId &&
      this._solapa(this._fromISO(f.fecha_desde), this._fromISO(f.fecha_hasta), this.fechaDesde, this.fechaHasta),
    );
    if (conflicto) {
      const donde = [conflicto.cliente, conflicto.instalacion, conflicto.puesto].filter(Boolean).join(' · ') || 'otro puesto';
      const nombre = (this.cubreSel ? `${this.cubreSel.apellidos} ${this.cubreSel.nombres}` : 'El eventual').trim();
      Swal.fire({
        icon: 'warning',
        title: 'Eventual ya asignado',
        html: `<b>${nombre}</b> ya está cubriendo en:<br><b>${donde}</b><br>` +
              `del ${this.fmt(this._fromISO(conflicto.fecha_desde))} al ${this.fmt(this._fromISO(conflicto.fecha_hasta))}.` +
              `<br><br>Elige otro eventual o ajusta las fechas.`,
      });
    }
  }

  // ¿Los rangos [a1,a2] y [b1,b2] se solapan?
  private _solapa(a1: Date | null, a2: Date | null, b1: Date | null, b2: Date | null): boolean {
    if (!a1 || !a2 || !b1 || !b2) { return false; }
    return a1.getTime() <= b2.getTime() && b1.getTime() <= a2.getTime();
  }

  get startAt(): Date {
    if (this.fechaDesde) { return this.fechaDesde; }
    const hoy = new Date();
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

  private _diasInclusive(d1: Date | null, d2: Date | null): number {
    if (!d1 || !d2) { return 0; }
    const diff = Math.round((d2.getTime() - d1.getTime()) / 86400000) + 1;
    return diff > 0 ? diff : 0;
  }
  calcularDias(): void {
    this.dias = this._diasInclusive(this.fechaDesde, this.fechaHasta);
  }

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
    const tienePuesto = !!this.asignacionId || !!this.clienteNombre;
    const tieneSale = !!this.saleSel || (this.esEdicion && !!this.saleCtrl.value);
    const cv = this.cubreCtrl.value;
    const tieneCubre = !!(typeof cv === 'string' ? cv.trim() : cv) || !!this.editCubreId;
    const tieneBackup = !!this.fechaDesde && !!this.fechaHasta;
    return tienePuesto && tieneSale && tieneCubre && tieneBackup;
  }

  guardar(): void {
    const out: any = {
      tipo: 'BACKUP',
      cliente: this.clienteNombre || '',
      asignacion: this.asignacionId,
      instalacion: this.instalacionNombre || '',
      puesto: this.puestoNombre || '',
      anio: this.anio || null,
      periodo: '',
      fecha_desde: this._toISO(this.fechaDesde),
      fecha_hasta: this._toISO(this.fechaHasta),
      dias: this.dias || 0,
      fecha_desde_pendiente: null,
      fecha_hasta_pendiente: null,
      dias_pendientes: 0,
    };
    if (this.saleSel) {
      out.persona_sale = `${this.saleSel.nombres} ${this.saleSel.apellidos}`.trim();
      out.persona_sale_ref = this.saleSel.id;
    } else {
      out.persona_sale = typeof this.saleCtrl.value === 'string' ? this.saleCtrl.value : '';
      out.persona_sale_ref = this.editSaleId;
    }
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
