import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule, MAT_DATE_LOCALE } from '@angular/material/core';
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
    MatDatepickerModule, MatNativeDateModule,
  ],
  providers: [{ provide: MAT_DATE_LOCALE, useValue: 'es-EC' }],
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
  fechaDesde: Date | null = null;
  fechaHasta: Date | null = null;
  dias: number | null = null;
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
      this.dias = (row.dias ?? null) as number | null;
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

    this.personaSrv.getPersonas({}).subscribe((ps) => { this.personasAll = ps || []; });
    this.saleFiltradas$ = this.filtro(this.saleCtrl);
    // "Quién cubre" solo puede ser personal de tipo SACAVACACIONES.
    this.cubreFiltradas$ = this.filtro(this.cubreCtrl, 'SACAVACACIONES');
  }

  private filtro(ctrl: FormControl, soloTipo?: string): Observable<Persona[]> {
    return ctrl.valueChanges.pipe(
      startWith(''),
      debounceTime(120),
      map((val: any) => {
        const base = soloTipo
          ? this.personasAll.filter(p => String(p.tipo || '').toUpperCase() === soloTipo)
          : this.personasAll;
        const q = (typeof val === 'string' ? val : this.displayPersona(val)).toLowerCase().trim();
        if (!q) { return base.slice(0, 50); }
        return base
          .filter(p => `${p.nombres || ''} ${p.apellidos || ''} ${p.cedula || ''}`.toLowerCase().includes(q))
          .slice(0, 50);
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

  // Días = contador de días calendario inclusive entre desde y hasta.
  calcularDias(): void {
    if (this.fechaDesde && this.fechaHasta) {
      const diff = Math.round((this.fechaHasta.getTime() - this.fechaDesde.getTime()) / 86400000) + 1;
      this.dias = diff > 0 ? diff : 0;
    } else {
      this.dias = 0;
    }
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
