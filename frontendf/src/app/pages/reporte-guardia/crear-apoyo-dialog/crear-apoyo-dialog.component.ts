import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { Observable } from 'rxjs';
import { debounceTime, startWith, map } from 'rxjs/operators';
import { ClienteService } from '../../../services/cliente.service';
import { InstalacionService } from '../../../services/instalacion.service';
import { PuestoService } from '../../../services/puesto.service';
import { PersonaService } from '../../../services/persona.service';
import { Cliente, Instalacion } from '../../../models';
import { Puesto } from '../../../models/puesto.model';
import { Persona } from '../../../models/persona.model';
import { ReporteGuardia } from '../../../models/reporte-guardia.model';

interface DialogData {
  row?: ReporteGuardia;      // presente = edición
  seccion?: string;          // sección (APOYO, DOBLADAS, ...); define qué campos se muestran
  cols?: string[];           // campos editables de esa sección
  titulo?: string;
}

@Component({
  selector: 'app-crear-apoyo-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule,
    MatFormFieldModule, MatInputModule, MatSelectModule, MatAutocompleteModule, MatButtonModule,
  ],
  templateUrl: './crear-apoyo-dialog.component.html',
  styleUrl: './crear-apoyo-dialog.component.css',
})
export class CrearApoyoDialogComponent implements OnInit {
  clientes: Cliente[] = [];
  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];
  personasAll: Persona[] = [];
  clienteId: number | null = null;
  instalacionId: number | null = null;
  puestoId: number | null = null;
  clienteCtrl = new FormControl<any>('');
  instalacionCtrl = new FormControl<any>('');
  puestoCtrl = new FormControl<any>('');
  personaCtrl = new FormControl<any>('');
  personasFiltradas$!: Observable<Persona[]>;
  personaSel: Persona | null = null;
  proviene = '';
  motivo = '';
  // Campos extra según la sección.
  valor: number | null = null;
  tipo = '';
  autorizacion = '';
  fechaEvento = '';   // yyyy-mm-dd
  esEdicion = false;
  seccion = 'APOYO';
  cols: string[] = ['cliente', 'puesto', 'persona_nombre', 'proviene', 'motivo'];
  titulo = '';
  private editPersonaId: number | null = null;

  constructor(
    private ref: MatDialogRef<CrearApoyoDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private clienteSrv: ClienteService,
    private instalacionSrv: InstalacionService,
    private puestoSrv: PuestoService,
    private personaSrv: PersonaService,
  ) {}

  ngOnInit(): void {
    const row = this.data?.row;
    this.esEdicion = !!row?.id;
    this.seccion = this.data?.seccion || (row?.seccion || 'APOYO');
    if (this.data?.cols && this.data.cols.length) { this.cols = this.data.cols; }
    this.titulo = this.data?.titulo || (this.esEdicion ? `Editar — ${this.seccion}` : `Crear ${this.seccion.toLowerCase()}`);

    if (row) {
      this.motivo = row.motivo || '';
      this.proviene = row.proviene || '';
      this.valor = (row as any).valor != null ? Number((row as any).valor) : null;
      this.tipo = (row as any).tipo || '';
      this.autorizacion = (row as any).autorizacion || '';
      const fe = (row as any).fecha_evento;
      this.fechaEvento = fe ? String(fe).slice(0, 10) : '';
      this.editPersonaId = (row as any).persona_ref ?? null;
      if (row.persona_nombre) { this.personaCtrl.setValue(row.persona_nombre); }
    }

    this.clienteSrv.getClientes().subscribe((cs) => {
      this.clientes = cs || [];
      if (row?.cliente) {
        const c = this.clientes.find(x => x.nombre_comercial === row.cliente);
        if (c) {
          this.clienteId = c.id!;
          this.clienteCtrl.setValue(c, { emitEvent: false });
          this.onCliente(row.puesto);
        }
      }
    });

    // Cargar todas las personas y filtrar localmente (dropdown poblado + filtrable).
    this.personaSrv.getPersonas({}).subscribe((ps) => { this.personasAll = ps || []; });
    this.personasFiltradas$ = this.personaCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(120),
      map((val: any) => {
        const q = (typeof val === 'string' ? val : this.displayPersona(val)).toLowerCase().trim();
        if (!q) { return this.personasAll.slice(0, 50); }
        const tokens = q.split(/\s+/).filter(Boolean);
        return this.personasAll
          .filter(p => {
            const hay = `${p.nombres || ''} ${p.apellidos || ''} ${p.cedula || ''}`.toLowerCase();
            return tokens.every(t => hay.includes(t));
          })
          .slice(0, 50);
      }),
    );
  }

  // ¿Se muestra este campo en esta sección?
  muestra(campo: string): boolean {
    return this.cols.includes(campo);
  }

  // Cliente -> carga sus instalaciones. En edición, ubica el puesto para preseleccionar.
  onCliente(preselectPuestoNombre?: string): void {
    this.instalaciones = [];
    this.puestos = [];
    if (!preselectPuestoNombre) {
      this.instalacionId = null; this.puestoId = null;
      this.instalacionCtrl.setValue('', { emitEvent: false });
      this.puestoCtrl.setValue('', { emitEvent: false });
    }
    if (!this.clienteId) { return; }
    this.instalacionSrv.getInstalaciones({ cliente_id: this.clienteId }).subscribe((is) => {
      this.instalaciones = is || [];
      const si = this.instalaciones.find(x => x.id === this.instalacionId);
      if (si) { this.instalacionCtrl.setValue(si, { emitEvent: false }); }
    });
    if (preselectPuestoNombre) {
      // Ubicar a qué instalación pertenece el puesto guardado para preseleccionar todo.
      this.puestoSrv.getPuestosPorCliente(this.clienteId).subscribe((ps) => {
        const p = (ps || []).find(x => x.nombre === preselectPuestoNombre);
        if (p) {
          this.instalacionId = p.instalacion_id ?? (p as any).instalacion ?? null;
          this.onInstalacion(preselectPuestoNombre);
        }
      });
    }
  }

  // Instalación -> carga sus puestos (se ve solo el nombre del puesto).
  onInstalacion(preselectPuestoNombre?: string): void {
    this.puestos = [];
    if (!preselectPuestoNombre) {
      this.puestoId = null;
      this.puestoCtrl.setValue('', { emitEvent: false });
    }
    if (!this.instalacionId) { return; }
    const si = this.instalaciones.find(x => x.id === this.instalacionId);
    if (si) { this.instalacionCtrl.setValue(si, { emitEvent: false }); }
    this.puestoSrv.getPuestosPorInstalacion(this.instalacionId).subscribe((ps) => {
      this.puestos = ps || [];
      if (preselectPuestoNombre) {
        const p = this.puestos.find(x => x.nombre === preselectPuestoNombre);
        if (p) { this.puestoId = p.id; this.puestoCtrl.setValue(p, { emitEvent: false }); }
      }
    });
  }

  // --- Autocompletar Cliente / Instalación / Puesto (escribir para filtrar) ---
  private _q(v: any): string { return (typeof v === 'string' ? v : '').toLowerCase().trim(); }

  clientesFiltrados(): Cliente[] {
    const q = this._q(this.clienteCtrl.value);
    if (!q) { return this.clientes; }
    return this.clientes.filter(c => (c.nombre_comercial || '').toLowerCase().includes(q));
  }
  instalacionesFiltradas(): Instalacion[] {
    const q = this._q(this.instalacionCtrl.value);
    if (!q) { return this.instalaciones; }
    return this.instalaciones.filter(i => `${i.nombre || ''} ${(i as any).codigo || ''}`.toLowerCase().includes(q));
  }
  puestosFiltrados(): Puesto[] {
    const q = this._q(this.puestoCtrl.value);
    if (!q) { return this.puestos; }
    return this.puestos.filter(p => (p.nombre || '').toLowerCase().includes(q));
  }

  displayCliente = (c: any): string => (c && typeof c !== 'string') ? (c.nombre_comercial || '') : (c || '');
  displayInstalacion = (i: any): string => (i && typeof i !== 'string') ? `${i.nombre || ''}${i.codigo ? ' (' + i.codigo + ')' : ''}` : (i || '');
  displayPuesto = (p: any): string => (p && typeof p !== 'string') ? (p.nombre || '') : (p || '');

  onClienteSel(c: Cliente): void {
    this.clienteId = c?.id ?? null;
    this.instalacionId = null; this.puestoId = null;
    this.instalacionCtrl.setValue('', { emitEvent: false });
    this.puestoCtrl.setValue('', { emitEvent: false });
    this.onCliente();
  }
  onInstalacionSel(i: Instalacion): void {
    this.instalacionId = i?.id ?? null;
    this.puestoId = null;
    this.puestoCtrl.setValue('', { emitEvent: false });
    this.onInstalacion();
  }
  onPuestoSel(p: Puesto): void {
    this.puestoId = p?.id ?? null;
  }

  displayPersona = (p: any): string => {
    if (!p) { return ''; }
    if (typeof p === 'string') { return p; }
    return `${p.nombres || ''} ${p.apellidos || ''}`.trim();
  };

  onPersonaSel(p: Persona): void {
    this.personaSel = p;
    this.proviene = p?.tipo || '';
  }

  get valido(): boolean {
    return !!this.clienteId && !!this.instalacionId && !!this.puestoId;
  }

  guardar(): void {
    const cli = this.clientes.find(c => c.id === this.clienteId);
    const pto = this.puestos.find(p => p.id === this.puestoId);
    const p = this.personaSel;
    const out: any = {
      cliente: cli?.nombre_comercial || '',
      puesto: pto?.nombre || '',            // solo el nombre del puesto
    };
    if (this.muestra('persona_nombre')) {
      if (p) {
        out.persona_nombre = `${p.nombres} ${p.apellidos}`.trim();
        out.persona_ref = p.id;
        out.proviene = p.tipo || '';
      } else {
        // Sin cambiar la persona: conservar la existente.
        out.persona_ref = this.editPersonaId;
        out.persona_nombre = typeof this.personaCtrl.value === 'string' ? this.personaCtrl.value : '';
        out.proviene = this.proviene || '';
      }
    }
    if (this.muestra('proviene') && !this.muestra('persona_nombre')) { out.proviene = this.proviene || ''; }
    if (this.muestra('valor')) { out.valor = this.valor == null || (this.valor as any) === '' ? 0 : Number(this.valor); }
    if (this.muestra('tipo')) { out.tipo = (this.tipo || '').trim(); }
    if (this.muestra('autorizacion')) { out.autorizacion = (this.autorizacion || '').trim(); }
    if (this.muestra('motivo')) { out.motivo = (this.motivo || '').trim(); }
    if (this.muestra('fecha_evento')) { out.fecha_evento = this.fechaEvento || null; }
    this.ref.close(out);
  }

  cancelar(): void {
    this.ref.close();
  }
}
