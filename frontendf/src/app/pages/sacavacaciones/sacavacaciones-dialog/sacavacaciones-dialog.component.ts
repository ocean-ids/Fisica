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
import { ClienteService } from '../../../services/cliente.service';
import { PersonaService } from '../../../services/persona.service';
import { Cliente } from '../../../models';
import { Persona } from '../../../models/persona.model';
import { ReporteVacaciones } from '../../../models/reporte-vacaciones.model';

interface DialogData {
  row?: ReporteVacaciones;   // presente = edición
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
  clientes: Cliente[] = [];
  personasAll: Persona[] = [];
  clienteId: number | null = null;

  // Persona que sale de vacaciones
  saleCtrl = new FormControl<any>('');
  saleFiltradas$!: Observable<Persona[]>;
  saleSel: Persona | null = null;

  // Persona que cubre (sacavacaciones)
  cubreCtrl = new FormControl<any>('');
  cubreFiltradas$!: Observable<Persona[]>;
  cubreSel: Persona | null = null;

  periodo = '';
  // Vacaciones (rango): al marcar Desde sugiere 15 días; el usuario hace clic en
  // el Hasta para fijar el día (puede ser el 15 o más).
  fechaDesde: Date | null = null;
  fechaHasta: Date | null = null;
  rangoForm = new FormGroup({
    start: new FormControl<Date | null>(null),
    end: new FormControl<Date | null>(null),
  });
  dias: number | null = null;
  // Referencia de 15 días (rango de comparación con "rayitas"): NO selecciona,
  // solo marca dónde caen los 15 días para no contar. El usuario fija el Hasta.
  compStart: Date | null = null;
  compEnd: Date | null = null;

  // Días pendientes: otro rango (mismo picker) por si no le dieron todas.
  fechaDesdePend: Date | null = null;
  fechaHastaPend: Date | null = null;
  rangoPendForm = new FormGroup({
    start: new FormControl<Date | null>(null),
    end: new FormControl<Date | null>(null),
  });
  diasPend: number | null = null;
  esEdicion = false;
  private editSaleId: number | null = null;
  private editCubreId: number | null = null;

  constructor(
    private ref: MatDialogRef<SacavacacionesDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private clienteSrv: ClienteService,
    private personaSrv: PersonaService,
  ) {}

  ngOnInit(): void {
    const row = this.data?.row;
    this.esEdicion = !!row?.id;
    if (row) {
      this.periodo = row.periodo || '';
      this.fechaDesde = this._fromISO(row.fecha_desde);
      this.fechaHasta = this._fromISO(row.fecha_hasta);
      this.rangoForm.setValue({ start: this.fechaDesde, end: this.fechaHasta });
      this._setRef(this.fechaDesde);
      this.dias = (row.dias ?? null) as number | null;
      this.fechaDesdePend = this._fromISO(row.fecha_desde_pendiente);
      this.fechaHastaPend = this._fromISO(row.fecha_hasta_pendiente);
      this.rangoPendForm.setValue({ start: this.fechaDesdePend, end: this.fechaHastaPend });
      this.diasPend = (row.dias_pendientes ?? null) as number | null;
      this.editSaleId = row.persona_sale_ref ?? null;
      this.editCubreId = row.sacavacaciones_ref ?? null;
      if (row.persona_sale) { this.saleCtrl.setValue(row.persona_sale); }
      if (row.sacavacaciones) { this.cubreCtrl.setValue(row.sacavacaciones); }
    }

    this.clienteSrv.getClientes().subscribe((cs) => {
      this.clientes = cs || [];
      if (row?.cliente) {
        const c = this.clientes.find(x => x.nombre_comercial === row.cliente);
        if (c) { this.clienteId = c.id!; }
      }
    });

    // Vacaciones: el rango se fija con dos clics (inicio + fin que elige el usuario).
    // Al marcar el Desde, la referencia de 15 días (rayitas) se coloca en Desde..+14.
    this.rangoForm.valueChanges.subscribe((v) => {
      this.fechaDesde = v.start ?? null;
      this.fechaHasta = v.end ?? null;
      this._setRef(this.fechaDesde);
      this.calcularDias();
    });
    // Rango de días pendientes.
    this.rangoPendForm.valueChanges.subscribe((v) => {
      this.fechaDesdePend = v.start ?? null;
      this.fechaHastaPend = v.end ?? null;
      this.diasPend = this._diasInclusive(this.fechaDesdePend, this.fechaHastaPend);
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
        // Todas las personas (o las que coinciden con la búsqueda).
        let base = q
          ? this.personasAll.filter(p => `${p.nombres || ''} ${p.apellidos || ''} ${p.cedula || ''}`.toLowerCase().includes(q))
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

  onSaleSel(p: Persona): void { this.saleSel = p; }
  onCubreSel(p: Persona): void { this.cubreSel = p; }

  // Coloca la referencia de 15 días (Desde .. Desde+14) para las "rayitas".
  private _setRef(desde: Date | null): void {
    if (desde) {
      this.compStart = desde;
      this.compEnd = new Date(desde.getFullYear(), desde.getMonth(), desde.getDate() + 14);
    } else {
      this.compStart = null;
      this.compEnd = null;
    }
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
    return !!this.clienteId && (!!this.saleSel || (this.esEdicion && !!this.saleCtrl.value));
  }

  guardar(): void {
    const cli = this.clientes.find(c => c.id === this.clienteId);
    const out: any = {
      cliente: cli?.nombre_comercial || '',
      periodo: (this.periodo || '').trim(),
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
